"""Revised H6 and H10 estimators; prospective, synthetic design only."""
import argparse
import json
import platform
import subprocess
import numpy as np
import scipy
from scipy.special import expit
from scipy.stats import t, norm
from longitudinal_checks import design, ar1
from mixed_checks import wilson


def cr2(x, y, mask, contrast, alpha=.04):
    """OLS, working-independence CR2, contrast-specific Satterthwaite df.

    x: participant x session x predictor; y/mask: participant x session.
    Padded missing rows have zero design and residual, so the leverage
    adjustment is identical to deleting them. Inference is approximate
    under nonidentity true covariance; MAR plus correct mean is required.
    """
    if not 0 < alpha < 1:
        raise ValueError('invalid alpha')
    if x.ndim != 3 or y.shape != x.shape[:2] or mask.shape != y.shape:
        raise ValueError('CR2 requires aligned participant/session arrays')
    if mask.dtype != np.bool_:
        raise ValueError('CR2 mask must be boolean')
    if contrast.shape != (x.shape[2],) or not np.isfinite(contrast).all():
        raise ValueError('invalid contrast')
    if not np.isfinite(x[mask]).all() or not np.isfinite(y[mask]).all():
        raise ValueError('observed design and outcomes must be finite')
    x = np.where(mask[..., None], x, 0.)
    y = np.where(mask, y, 0.)
    _, k, p = x.shape
    active = mask.any(axis=1)
    x, y = x[active], y[active]
    info = np.einsum('gki,gkj->ij', x, x)
    if len(x) <= p or np.linalg.matrix_rank(info) < p:
        raise ValueError('insufficient observed clusters or rank')
    bread = np.linalg.inv(info)
    beta = bread @ np.einsum('gki,gk->i', x, y)
    residual = y - x @ beta
    h = x @ bread @ x.transpose(0, 2, 1)
    ev, u = np.linalg.eigh(np.eye(k) - h)
    if ev.min() <= 1e-10:
        raise ValueError('singular cluster leverage')
    v = (u @ ((u.transpose(0, 2, 1) @ (x @ bread @ contrast)[..., None])
              / np.sqrt(ev)[..., None]))[..., 0]
    se = float(np.sqrt(np.sum((v * residual).sum(axis=1)**2)))
    w = np.einsum('gki,gk->gi', x, v)
    gram = np.diag(np.sum(v*v, axis=1)) - w @ bread @ w.T
    df = float(np.trace(gram)**2 / np.sum(gram*gram))
    if not np.isfinite([se, df]).all() or se <= 0 or df <= 0:
        raise ValueError('invalid contrast variance or df')
    return float(contrast @ beta), float(t.ppf(1-alpha/2, df)*se), df


def endpoint_design(rng, n, retention, effect, mode):
    """New H10 design: first/last measurements, independent final offer."""
    if n < 40 or n % 2 or not 0 < retention < 1 or mode not in ('none','mar','mnar'):
        raise ValueError('invalid design')
    z = np.arange(n) % 2
    e = ar1(rng, n, 8, .45)
    u = rng.normal(size=n)
    b = .3*u + .35*rng.normal(size=n)
    y0 = .2*z + u + e[:,0]*(.8+.4*z)
    y1 = .1+.2*z+effect*z+u+b+e[:,-1]*(.8+.4*z)
    if mode == 'none':
        m = np.ones(n, dtype=bool)
    else:
        p = expit(np.log(retention/(1-retention))+.35*y0-.15*z+
                  (.65*e[:,-1] if mode == 'mnar' else 0))
        m = rng.random(n) < p
    return z, y0, np.where(m, y1, np.nan), m


def endpoint(z, y0, y1, mask, shifts=(0., 0.)):
    """Arm-specific regression standardization of change scores.

    Mean of predicted change over ALL assigned first-session outcomes.
    Influence function accounts for fitted regressions and empirical
    covariate distribution, including fixed-delta missing-outcome shifts.
    This is outcome-regression MAR, not double robust or MNAR identified.
    """
    if any(a.ndim != 1 for a in (z, y0, y1, mask)) or not (len(z) == len(y0) == len(y1) == len(mask)):
        raise ValueError('endpoint inputs must be aligned one-dimensional arrays')
    if not np.isin(z, (0, 1)).all():
        raise ValueError('assignment must contain only arm codes 0 and 1')
    if mask.dtype != np.bool_:
        raise ValueError('endpoint mask must be boolean')
    if not np.isfinite(y1[mask]).all():
        raise ValueError('observed endpoint ratings must be finite')
    if not np.isfinite(y0).all():
        raise ValueError('first-session missingness requires separate model')
    shifts = np.asarray(shifts, dtype=float)
    if shifts.shape != (2,) or not np.isfinite(shifts).all():
        raise ValueError('shifts must contain two finite arm-specific values')
    means, variances = [], []
    for arm in (0, 1):
        q = z == arm
        a, d, s = y0[q], y1[q]-y0[q], mask[q]
        x = np.column_stack([np.ones(len(a)), a])
        xo, do = x[s], d[s]
        if len(do) <= 2 or np.linalg.matrix_rank(xo) < 2:
            raise ValueError('insufficient endpoint observations')
        bread = np.linalg.inv(xo.T @ xo)
        beta = bread @ xo.T @ do
        pred = x @ beta + shifts[arm]*(~s)
        mu = pred.mean()
        residual = np.where(s, d-x @ beta, 0.)
        influence = pred-mu + len(a)*(x @ bread @ x.mean(axis=0))*residual
        means.append(mu)
        variances.append(np.var(influence, ddof=1)/len(a))
    return float(means[1]-means[0]), float(norm.ppf(.975)*np.sqrt(sum(variances)))


def summary(vals, truth, reps):
    if reps < 2 or len(vals) > reps:
        raise ValueError('invalid replication counts')
    if not vals:
        return dict(valid=0, requested=reps, failed=reps, bias=None,
                    rejection=None, coverage=None, rejection_mc_interval=None,
                    coverage_mc_interval=None, bias_mcse=None)
    a = np.asarray(vals)
    est, rad = a[:,0], a[:,1]
    if not np.isfinite(a).all() or np.any(rad < 0):
        raise ValueError('invalid replication estimates or intervals')
    rejects = int(np.sum(np.abs(est)>rad))
    covers = int(np.sum(np.abs(est-truth)<=rad))
    return dict(valid=len(a), requested=reps, failed=reps-len(a), bias=float(est.mean()-truth),
                rejection=rejects/len(a), coverage=covers/len(a),
                rejection_mc_interval=wilson(rejects,len(a)),
                coverage_mc_interval=wilson(covers,len(a)),
                bias_mcse=float(est.std(ddof=1)/np.sqrt(len(a))) if len(a)>1 else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reps', type=int, default=2000)
    args = parser.parse_args()
    if args.reps < 2:
        parser.error('reps >= 2')
    out = dict(sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
               python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
               reps=args.reps, h6={}, h10={})
    for alpha, seed in ((.05,20261126),(.04,20261201)):
        for mode in ('none','mar','mnar'):
            for effect in (0.,-.25):
                rng = np.random.default_rng(seed)
                vals, failures = [], {}
                for _ in range(args.reps):
                    x,y,g,c,m,_,_ = design(rng,'h6',80,8,effect,mode)
                    try:
                        vals.append(cr2(x.reshape(80,8,-1),y.reshape(80,8),m.reshape(80,8),c,alpha))
                    except (ValueError, np.linalg.LinAlgError) as exc:
                        reason = str(exc)
                        failures[reason] = failures.get(reason, 0) + 1
                result = summary(vals,effect,args.reps)
                result.update(seed=seed, n=80, sessions=8, alpha=alpha,
                              missing=mode, truth=effect, failure_reasons=failures)
                result['mean_df'] = float(np.mean(np.asarray(vals)[:,2])) if vals else None
                out['h6'][f'{alpha}_{mode}_{effect}'] = result
    for n in (600,800,1000):
        for mode in ('none','mar','mnar'):
            for effect in (0.,-.35):
                rng = np.random.default_rng(20261127+n)
                vals, retained, failures = [], [], {}
                for _ in range(args.reps):
                    z,y0,y1,m = endpoint_design(rng,n,.85,effect,mode)
                    retained.append(m.mean())
                    try:
                        vals.append(endpoint(z,y0,y1,m))
                    except (ValueError, np.linalg.LinAlgError) as exc:
                        reason = str(exc)
                        failures[reason] = failures.get(reason, 0) + 1
                result = summary(vals,effect,args.reps)
                result.update(seed=20261127+n, n=n, sessions=8, alpha=.05,
                              missing=mode, truth=effect, failure_reasons=failures)
                result['retention'] = float(np.mean(retained))
                out['h10'][f'{n}_{mode}_{effect}'] = result
    print(json.dumps(out,indent=2,allow_nan=False))
    # Preserve diagnostic output but fail the run if any fit failed.
    if any(row['failed'] for kind in ('h6', 'h10') for row in out[kind].values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
