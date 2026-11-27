"""Synthetic bounded-rating design calibration; never empirical results."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.special import ndtr, expit
from scipy.stats import t, norm

SEED = 1729
TARGET = 480
CAP = 560


def covariates(rng, n, rho):
    common = rng.normal(size=(n, 1))
    independent = rng.normal(size=(n, 4))
    motives = 10 * ndtr(np.sqrt(rho) * common + np.sqrt(1-rho) * independent)
    pre = rng.uniform(0, 10, n)
    age = rng.integers(18, 75, n)
    experience = rng.uniform(0, 10, n)
    use_days = rng.integers(0, 31, n)
    recency = rng.integers(0, 31, n)
    source = rng.choice(3, size=n, p=[.3, .6, .1])
    return np.column_stack([np.ones(n), motives, pre, age, experience,
                            use_days, recency, source == 1, source == 2])


def calibration(rho, partial_r):
    # Independent reference sample; exact linear conditional mean in the DGP.
    x = covariates(np.random.default_rng(SEED + 99), 100_000, rho)
    z = np.delete(x, 1, axis=1)
    residual = x[:, 1] - z @ np.linalg.lstsq(z, x[:, 1], rcond=None)[0]
    sigma = 2 / np.sqrt(3)
    return partial_r * sigma / (np.std(residual) * np.sqrt(1 - partial_r**2))


def trial(rng, rho, beta, missing, *, target=TARGET, cap=CAP):
    x = covariates(rng, cap, rho)
    y = (5 + .25*(x[:, 5]-5) + beta*(x[:, 1]-5)
         + .12*(x[:, 2]-5) + rng.uniform(-2, 2, cap))
    if np.any((y < 0) | (y > 10)):
        raise ValueError("DGP exceeded rating bounds; revise calibration")
    # MAR: post-clarity missingness depends on observed expression and pre-clarity.
    observed = np.ones(cap, dtype=bool)
    if missing:
        probability = expit(-2.2 + .12*(x[:, 1]-5) - .16*(x[:, 5]-5))
        observed = rng.uniform(size=cap) >= probability
    ids = np.flatnonzero(observed)[:target]
    x, y = x[ids], y[ids]
    n, p = x.shape
    inv = np.linalg.inv(x.T @ x)
    coef = inv @ x.T @ y
    resid = y - x @ coef
    leverage = np.einsum("ij,jk,ik->i", x, inv, x)
    weights = (resid / (1-leverage))**2
    se = np.sqrt((inv @ (x.T @ (x*weights[:, None])) @ inv)[1, 1])
    critical = t.ppf(.975, n-p)
    return n, coef[1], abs(coef[1]/se) > critical, abs(coef[1]-beta) <= critical*se


def wilson(success, total):
    z = norm.ppf(.975)
    p = success/total
    den = 1+z*z/total
    center = (p+z*z/(2*total))/den
    half = z*np.sqrt(p*(1-p)/total+z*z/(4*total**2))/den
    return [float(center-half), float(center+half)]


def simulate(reps=2000, seed=SEED, *, target=TARGET, cap=CAP):
    if reps < 1 or target < 20 or cap < target:
        raise ValueError("invalid replications or recruitment sizes")
    rows = []
    for rho in (.2, .6):
        for partial_r in (0., .15):
            beta = calibration(rho, partial_r)
            for missing in (False, True):
                rng = np.random.default_rng(np.random.SeedSequence([seed, int(rho*10), int(partial_r*100), int(missing)]))
                a = np.array([trial(rng, rho, beta, missing, target=target, cap=cap) for _ in range(reps)])
                rejected, covered = int(a[:, 2].sum()), int(a[:, 3].sum())
                rows.append(dict(rho=rho, target_partial_r=partial_r, beta=float(beta),
                    mar_outcome_missing=missing, reps=reps, mean_n=float(a[:,0].mean()),
                    target_attainment=float(np.mean(a[:,0]==target)),
                    bias=float(a[:,1].mean()-beta), rejection_rate=rejected/reps,
                    rejection_ci95=wilson(rejected,reps), coverage=covered/reps,
                    coverage_ci95=wilson(covered,reps)))
    return {"data_kind":"synthetic", "seed":seed, "target_complete":target,
            "submission_cap":cap, "scenarios":rows}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reps", type=int, default=2000)
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument("--target", type=int, default=TARGET)
    p.add_argument("--cap", type=int, default=CAP)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.out.write_text(json.dumps(simulate(a.reps, a.seed, target=a.target, cap=a.cap), indent=2, allow_nan=False)+"\n")
