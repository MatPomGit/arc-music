"""Prospective calibration screen for H6 and H10; synthetic data only.

H6: same Gaussian profile ML point estimate, participant-cluster score
sandwich with CR1 multiplier and conservative t(G-p) reference.
H10: marginal quadratic arm-by-time regression, working independence,
cluster sandwich; estimated retention-IPW comparator. No MNAR correction.
"""
import argparse
import json
import platform
import subprocess
import numpy as np
import scipy
from scipy.stats import t
from longitudinal_checks import design, fit
from mixed_checks import (blocks, covariance, mixed_fit,
                          estimated_probability, diagnostic_summary)


def cluster_gls(data, theta, beta, contrast):
    """Fixed fitted covariance GLS scores, one row per observed participant."""
    p = len(beta)
    info = np.zeros((p, p))
    meat = np.zeros((p, p))
    groups = count = 0
    for x, y, z, v, distance in data:
        cov = covariance(theta, z, v, distance)
        l = np.linalg.cholesky(cov)
        wx = np.linalg.solve(l, x)
        wr = np.linalg.solve(l, (y - x @ beta)[..., None])[..., 0]
        scores = np.einsum('nki,nk->ni', wx, wr)
        info += np.einsum('nki,nkj->ij', wx, wx)
        meat += scores.T @ scores
        groups += len(y)
        count += y.size
    if groups <= p or count <= p or np.linalg.matrix_rank(info) < p:
        raise ValueError('insufficient observed clusters or rank')
    bread = np.linalg.inv(info)
    var = bread @ meat @ bread
    var *= groups/(groups-1) * (count-1)/(count-p)
    se = float(np.sqrt(max(0., contrast @ var @ contrast)))
    if not np.isfinite(se) or se <= 0:
        raise ValueError('invalid robust standard error')
    return float(contrast @ beta), float(t.ppf(.975, groups-p)*se)


def h6_estimates(x, y, g, c, mask, n, k):
    mixed = mixed_fit(x, y, mask, n, k, 'h6', c)
    robust = cluster_gls(blocks(x, y, mask, n, k, 'h6'),
                         np.asarray(mixed['theta']), np.asarray(mixed['beta']), c)
    return (mixed['estimate'], mixed['radius']), robust


def h10_estimates(x, y, g, c, mask, n, k):
    p = estimated_probability(x, y, mask, n, k, 'h10')
    return (fit(x[mask], y[mask], g[mask], c)[:2],
            fit(x[mask], y[mask], g[mask], c, 1/p[mask])[:2])


def screen(kind, missing, effect, n, k=8, reps=500, seed=91307):
    if kind not in ('h6', 'h10') or missing not in ('none', 'mar', 'mnar'):
        raise ValueError('unknown scenario')
    if n < 40 or n % 2 or k < 4 or reps < 2:
        raise ValueError('require even n>=40, k>=4, reps>=2')
    rng = np.random.default_rng(seed)
    names = ('model_based', 'cluster_gls') if kind == 'h6' else ('marginal', 'estimated_ipw')
    values = {name: [] for name in names}
    retained = []
    for _ in range(reps):
        x, y, g, c, mask, _, _ = design(rng, kind, n, k, effect, missing)
        retained.append(float(mask.reshape(n,k)[:, -1].mean()))
        y = np.where(mask, y, np.nan)
        try:
            a, b = (h6_estimates if kind == 'h6' else h10_estimates)(
                x, y, g, c, mask, n, k)
        except (ValueError, np.linalg.LinAlgError):
            continue
        if not np.isfinite([*a, *b]).all():
            continue
        for name, result in zip(names, (a, b)):
            values[name].append(result)
    return {'n': n, 'k': k, 'effect': effect, 'missing': missing,
            'mean_last_observed_fraction': float(np.mean(retained)),
            'paired_valid': len(values[names[0]]),
            'methods': {name: diagnostic_summary(v, effect, reps)
                        for name, v in values.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', required=True, choices=['h6','h10'])
    parser.add_argument('--missing', required=True, choices=['none','mar','mnar'])
    parser.add_argument('--reps', type=int, default=500)
    parser.add_argument('--seed', type=int, default=91307)
    parser.add_argument('--n', type=int, nargs='+')
    a = parser.parse_args()
    sizes = a.n or ([80] if a.kind == 'h6' else [160,400,800,1200])
    alt = -.25 if a.kind == 'h6' else -.35
    out = {'sha': subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
           'python': platform.python_version(), 'numpy': np.__version__,
           'scipy': scipy.__version__, 'seed': a.seed, 'reps': a.reps,
           'kind': a.kind, 'missing': a.missing,
           'results': [screen(a.kind,a.missing,effect,n,reps=a.reps,
                              seed=a.seed+n) for n in sizes for effect in (0.,alt)]}
    print(json.dumps(out, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
