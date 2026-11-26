"""Synthetic marginal-regression diagnostics for H6/H8/H10, not empirical effects.
Random-slope/serial DGP; cluster sandwich estimates population contrasts. These
are not mixed-model likelihood fits. Oracle weights are a benchmark, not a
practical MNAR remedy. Pattern-mixture shifts report point sensitivity only.
"""
import argparse
import json
import platform
import subprocess
import numpy as np
import scipy
from scipy.special import expit
from scipy.stats import t


def fit(x, y, groups, contrast, weights=None):
    """WLS and cluster sandwich with participant degrees of freedom."""
    x, y = np.asarray(x), np.asarray(y)
    groups, contrast = np.asarray(groups), np.asarray(contrast)
    w = np.ones(len(y)) if weights is None else np.asarray(weights)
    g, idx = np.unique(groups, return_inverse=True)
    n, p = x.shape
    if len(g) <= p or n <= p or np.linalg.matrix_rank(x) < p:
        raise ValueError('insufficient independent clusters or rank')
    if np.any(w <= 0) or not np.isfinite(w).all():
        raise ValueError('invalid weights')
    bread = np.linalg.inv(x.T @ (w[:, None] * x))
    b = bread @ (x.T @ (w*y))
    scores = np.zeros((len(g), p))
    np.add.at(scores, idx, x*(w*(y-x@b))[:,None])
    cov = bread @ (scores.T@scores) @ bread
    cov *= len(g)/(len(g)-1)*(n-1)/(n-p)
    estimate = float(contrast@b)
    radius = float(t.ppf(.975,len(g)-1)*np.sqrt(max(0.,contrast@cov@contrast)))
    return estimate, radius, b


def ar1(rng, n, k, phi):
    e = rng.normal(size=(n,k))
    for j in range(1,k):
        e[:,j] = phi*e[:,j-1] + np.sqrt(1-phi**2)*e[:,j]
    return e


def center(x):
    m = np.broadcast_to(x.mean(axis=1,keepdims=True),x.shape)
    return x-m, m


def design(rng, kind, n, k, effect, missing):
    ids = np.repeat(np.arange(n),k)
    z = np.repeat(np.arange(n)%2,k).reshape(n,k)
    time = np.broadcast_to(np.linspace(0,1,k),(n,k))
    e = ar1(rng,n,k,.45)
    u = rng.normal(size=(n,1))
    b = .3*u+.35*rng.normal(size=(n,1))
    if kind == 'h6':
        q = ar1(rng,n,k,.35)+.5*rng.normal(size=(n,1))
        d = rng.normal(size=(n,k))+.3*u
        relief = .3*d+rng.normal(size=(n,k))
        lagq = np.column_stack([np.zeros(n),q[:,:-1]])
        lagd = np.column_stack([np.zeros(n),d[:,:-1]])
        qw,qb = center(q)
        cols = [np.ones_like(q),qw,qb,*center(d),*center(relief),*center(lagq),*center(lagd),time]
        x = np.stack(cols,axis=-1)
        beta = np.array([0,effect,.15,.2,.1,.3,.1,.12,.08,.15,.1,.1])
        y = x@beta+u+b*qw+e*(.7+.3*expit(d))
        c = np.eye(len(beta))[1]
        p_mar = np.ones_like(y) if missing == 'none' else expit(1.7-.5*q-.3*d)
        p_true = p_mar if missing != 'mnar' else expit(1.7-.5*q-.3*d-.9*e)
        mask = rng.random(y.shape)<p_true if missing!='none' else np.ones_like(y,dtype=bool)
    elif kind == 'h10':
        # Quadratic basis vanishes at both contrast endpoints.
        h = time*(1-time)
        x = np.stack([np.ones_like(time),z,time,z*time,h,z*h],axis=-1)
        beta = np.array([0,.2,.1,effect,.2,-.25])
        y = x@beta+u+b*time+e*(.8+.4*z)
        c = np.eye(len(beta))[3]
        mask = np.ones_like(y,dtype=bool)
        p_mar,p_true = np.ones_like(y),np.ones_like(y)
        if missing!='none':
            for j in range(1,k):
                pm = expit(2.6-.4*z[:,j]+.4*y[:,j-1])
                pt = pm if missing=='mar' else expit(2.6-.4*z[:,j]+.4*y[:,j-1]+.65*e[:,j])
                mask[:,j] = mask[:,j-1] & (rng.random(n)<pt)
                p_mar[:,j]=p_mar[:,j-1]*pm
                p_true[:,j]=p_true[:,j-1]*pt
    else:
        raise ValueError('unknown design')
    return x.reshape(n*k,-1),y.ravel(),ids,c,mask.ravel(),p_mar.ravel(),p_true.ravel()


def summarize(values, truth, requested):
    a=np.asarray(values)
    if not len(a): raise ValueError('no valid replicates')
    est,rad=a.T
    reject=np.mean(np.abs(est)>rad)
    cover=np.mean(np.abs(est-truth)<=rad)
    return dict(valid=len(est),requested=requested,bias=float(np.mean(est)-truth),
                rejection=float(reject),coverage=float(cover),
                mcse=float(np.sqrt(reject*(1-reject)/len(est))),
                coverage_mcse=float(np.sqrt(cover*(1-cover)/len(est))))


def longitudinal(kind, n=120, k=8, effect=-.25, missing='none', reps=300, seed=1729):
    if kind not in ('h6','h10') or missing not in ('none','mar','mnar') or n<40 or k<4 or reps<2:
        raise ValueError('invalid scenario')
    rng=np.random.default_rng(seed)
    methods={m:[] for m in ('complete','observed_weighted','oracle_weighted')}
    shifts={str(d):[] for d in (-.5,0.,.5)}
    retained=[]
    for _ in range(reps):
        x,y,g,c,mask,pm,pt=design(rng,kind,n,k,effect,missing)
        retained.append(mask.mean())
        try:
            a,r,b=fit(x[mask],y[mask],g[mask],c)
            obs=fit(x[mask],y[mask],g[mask],c,1/pm[mask])[:2]
            oracle=fit(x[mask],y[mask],g[mask],c,1/pt[mask])[:2]
            delta_values={}
            for d in (-.5,0.,.5):
                imp=y.copy()
                # H6: shift by within-person rumination; H10: by arm.
                imp[~mask]=x[~mask]@b+d*x[~mask,1]
                delta_values[str(d)]=fit(x,imp,g,c)[0]
        except (ValueError,np.linalg.LinAlgError):
            continue
        methods['complete'].append((a,r)); methods['observed_weighted'].append(obs); methods['oracle_weighted'].append(oracle)
        for d,v in delta_values.items(): shifts[d].append(v)
    return dict(methods={m:summarize(v,effect,reps) for m,v in methods.items()},
                retention=float(np.mean(retained)), shift_means={d:float(np.mean(v)) for d,v in shifts.items()})


def expertise(n=240,effect=-.3,reps=500,seed=1730):
    """H8 reduced-control × continuous expertise, heterogeneous outcome error."""
    if n<20 or n%2 or reps<2: raise ValueError('invalid scenario')
    rng=np.random.default_rng(seed); out=[]; z=np.arange(n)%2-.5
    for _ in range(reps):
        q=rng.normal(size=n); familiarity=.5*q+rng.normal(size=n)
        ai=rng.normal(size=n); identity=.6*q+rng.normal(size=n)
        x=np.column_stack([np.ones(n),z,q,z*q,familiarity,ai,identity])
        y=x@np.array([0,-.2,.1,effect,.15,.1,.1])+rng.normal(size=n)*(.6+.8*expit(q+z))
        out.append(fit(x,y,np.arange(n),np.eye(7)[3])[:2])
    return summarize(out,effect,reps)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--seed',type=int,default=1730); p.add_argument('--reps',type=int,default=300)
    a=p.parse_args()
    results=dict(sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),seed=a.seed,python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__)
    for kind,effect in [('h6',-.25),('h10',-.35)]:
        results[kind]={f'{m}_{e}':longitudinal(kind,effect=e,missing=m,reps=a.reps,seed=a.seed) for m in ('none','mar','mnar') for e in (0.,effect)}
    results['h8']={str(e):expertise(effect=e,reps=a.reps,seed=a.seed) for e in (0.,-.3)}
    print(json.dumps(results,indent=2,allow_nan=False,sort_keys=True))

if __name__=='__main__': main()
