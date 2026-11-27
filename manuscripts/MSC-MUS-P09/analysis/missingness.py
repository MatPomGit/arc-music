"""Sensitivity analyses of the full assigned-cohort marginal contrast."""
import argparse
import json
import itertools

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from inference import MODELS, prepare

DELTAS = tuple(itertools.product((-2, -1, 0, 1, 2), repeat=2))
COVARIATES = ["understanding0", "distance0", "importance0", "training", "prior_use_days"]
SCALE = np.array([10., 10., 10., 1., 30.])


def covariates(d):
    x = d[COVARIATES].to_numpy(float) / SCALE
    if not np.isfinite(x).all():
        raise ValueError("Missing or nonfinite baseline covariates")
    return np.column_stack((np.ones(len(x)), x))


def response_probability(x, observed):
    """Fixed weak ridge on slopes only; no silent weight truncation."""
    if not observed.any():
        raise ValueError("No observed outcomes in assigned arm")
    if observed.all():
        return np.ones(len(x))
    penalty = np.r_[0., np.full(x.shape[1]-1, .1)]
    y = observed.astype(float)

    def loss(b):
        eta = x @ b
        return (np.logaddexp(0., eta).sum() - y @ eta
                + .5 * np.sum(penalty * b*b))

    def grad(b):
        return x.T @ (expit(x @ b)-y) + penalty*b

    fit = minimize(loss, np.zeros(x.shape[1]), jac=grad, method="BFGS",
                   options={"gtol": 1e-6, "maxiter": 300})
    if not fit.success and np.linalg.norm(grad(fit.x), ord=np.inf) > 1e-5:
        raise ValueError("Response model failed to converge")
    prob = expit(x @ fit.x)
    if not np.isfinite(prob).all() or np.any(prob <= 1e-8):
        raise ValueError("Numerical positivity failure")
    return prob


def arm_estimates(d, outcome):
    if d.empty:
        raise ValueError("Empty assigned arm")
    x = covariates(d)
    y = d[outcome].to_numpy(float)
    obs = np.isfinite(y)
    if np.any((y[obs] < 0) | (y[obs] > 10)):
        raise ValueError("Observed score outside [0,10]")
    if not obs.any():
        raise ValueError("No observed outcomes in assigned arm")
    prob = response_probability(x, obs)
    w = 1 / prob[obs]
    ess = float(w.sum()**2 / (w @ w))
    ipw = float(np.average(y[obs], weights=w))
    diag = dict(n=len(y), observed=int(obs.sum()), min_probability=float(prob.min()),
                max_weight=float(w.max()), effective_n=ess,
                positivity_warning=bool(prob.min() < .05 or ess < .5*obs.sum()))
    shifts = None
    if obs.all():
        shifts = {delta: float(y.mean()) for delta in range(-2, 3)}
    elif obs.sum() > x.shape[1] and np.linalg.matrix_rank(x[obs]) == x.shape[1]:
        beta = np.linalg.lstsq(x[obs], y[obs], rcond=None)[0]
        pred = x[~obs] @ beta
        shifts = {delta: float((y[obs].sum() + np.clip(pred+delta, 0, 10).sum())/len(y))
                  for delta in range(-2, 3)}
    return ipw, diag, shifts


def points(d, outcome):
    a0, a1 = [arm_estimates(d[d.music == z], outcome) for z in (0, 1)]
    estimates = {"ipw": a1[0]-a0[0]}
    if a0[2] is not None and a1[2] is not None:
        estimates.update({f"shift_{a}/{b}": a1[2][b]-a0[2][a] for a, b in DELTAS})
    return estimates, [a0[1], a1[1]]


def resample(d, rng):
    # Preserve the realised allocation and baseline training strata.
    # Resample whole participants, not item scores or measurement occasions.
    groups = d.groupby(["music", "training"], sort=True).indices
    indices = np.concatenate([rng.choice(g, len(g), replace=True) for g in groups.values()])
    return d.iloc[indices].reset_index(drop=True)


def sensitivity_endpoint(d, outcome, status, reps=999, seed=20261127):
    if reps < 2:
        raise ValueError("At least two bootstrap replications required")
    counts = {str(a): {k: int((d.loc[d.music == a, status] == k).sum())
                       for k in ("defined", "undefined", "unknown")} for a in (0, 1)}
    report = dict(target_status=counts, bootstrap_requested=reps)
    if not d[status].eq("defined").all():
        report["unavailable"] = "Full-cohort outcome undefined or unresolved; no hypothetical numerical score assigned"
        return report
    try:
        estimate, diagnostics = points(d, outcome)
    except (ValueError, np.linalg.LinAlgError) as exc:
        report["unavailable"] = str(exc)
        return report
    report["response_diagnostics"] = diagnostics
    report["shift_model_available"] = len(estimate) == 26
    draws = {k: [] for k in estimate}
    rng = np.random.default_rng(seed)
    for _ in range(reps):
        try:
            values, _ = points(resample(d, rng), outcome)
        except (ValueError, np.linalg.LinAlgError):
            continue
        for k in draws.keys() & values.keys():
            draws[k].append(values[k])
    report["estimates"] = {}
    for key, value in estimate.items():
        valid = draws[key]
        # Withhold intervals when >5% fail; small smoke runs are descriptive only.
        ci = ([float(v) for v in np.quantile(valid, [.025, .975])]
              if len(valid) >= max(2, np.ceil(.95*reps)) else None)
        report["estimates"][key] = dict(contrast=float(value), ci=ci,
                                        successful=len(valid), failed=reps-len(valid))
    return report


def analyze_missingness(frame, reps=999, seed=20261127):
    d = prepare(frame)
    seeds = np.random.SeedSequence(seed).spawn(len(MODELS))
    return dict(schema_version=1, seed=seed, bootstrap_requested=reps,
                interval="pointwise percentile; conditional on fixed arm/training counts",
                hypotheses={h: sensitivity_endpoint(d, o, "target_status2" if h == "H1" else "target_status1",
                                                    reps, s)
                            for (h, (o, _)), s in zip(MODELS.items(), seeds)})


def demo(reps, seed):
    from calibration import generate
    rng = np.random.default_rng(seed)
    result = {}
    for mechanism in ("MCAR", "MAR", "MNAR"):
        d = generate(rng, 588, "standard", mechanism, "alternative")
        d["target_status2"] = "defined"
        result[mechanism] = sensitivity_endpoint(d, "understanding2", "target_status2", reps, seed)
    return dict(synthetic=True, seed=seed, truth=.5, scenarios=result,
                note="Single synthetic sample per mechanism; not coverage calibration")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="?")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--reps", type=int, default=999)
    parser.add_argument("--seed", type=int, default=20261127)
    args = parser.parse_args()
    if args.demo == bool(args.csv):
        parser.error("Provide exactly one of CSV or --demo")
    result = (demo(args.reps, args.seed) if args.demo else
              analyze_missingness(pd.read_csv(args.csv, dtype={"participant_id": str}), args.reps, args.seed))
    print(json.dumps(result, indent=2, allow_nan=False))
