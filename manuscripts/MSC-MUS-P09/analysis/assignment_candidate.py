"""Development candidate for defined-outcome missingness inference (E3-P09-001).

Not an approved confirmatory analysis. The same callable is used by the
calibration driver and the ledger-reconciled candidate CLI.
"""
import argparse
import json
import math
import numpy as np
import pandas as pd
from inference import MODELS, prepare, holm
from missingness import arm_estimates, resample

MIN_DRAWS = 199


def point(d, outcome):
    arm0, arm1 = (arm_estimates(d[d.music == a], outcome, include_shifts=False) for a in (0, 1))
    return float(arm1[0] - arm0[0]), [arm0[1], arm1[1]]


def centered_test(estimate, draws, alpha=.05):
    """Absolute centered bootstrap errors, conservative plus-one p-value."""
    draws = np.asarray(draws, float)
    if not np.isfinite(estimate) or draws.ndim != 1 or not np.isfinite(draws).all():
        raise ValueError("Invalid bootstrap estimates")
    n = len(draws)
    k = math.ceil((1-alpha)*(n+1))
    if not 1 <= k <= n:
        raise ValueError("Too few successful draws")
    error = np.abs(draws-estimate)
    radius = float(np.partition(error, k-1)[k-1])
    if radius <= 0:
        raise ValueError("Degenerate bootstrap uncertainty")
    p = float((1 + np.count_nonzero(error >= abs(estimate)))/(n+1))
    return {"contrast": estimate, "ci": [estimate-radius, estimate+radius], "p": p}


def candidate_test(d, outcome, status, reps=999, seed=20261127, *, point_estimator=None):
    """Full assigned cohort marginal contrast under defined target and MAR.

    Response probabilities are refitted separately within each arm on every
    participant bootstrap, preserving realised arm/training stratum counts.
    Unresolved/undefined targets and insufficient overlap fail closed.
    """
    estimator = point if point_estimator is None else point_estimator
    if reps < MIN_DRAWS:
        raise ValueError("At least 199 bootstrap draws required")
    result = {"candidate_available": False, "confirmatory_available": False,
              "requested": reps, "attempted": 0, "successful": 0, "failed": 0,
              "label": "development candidate; not authorized for confirmatory inference"}
    if not d[status].eq("defined").fillna(False).all():
        return dict(result, unavailable="Full-cohort target undefined or unresolved")
    try:
        estimate, diagnostics = estimator(d, outcome)
    except (ValueError, np.linalg.LinAlgError) as exc:
        return dict(result, unavailable=str(exc))
    result.update(contrast=estimate, response_diagnostics=diagnostics)
    if any(a["positivity_warning"] for a in diagnostics):
        return dict(result, unavailable="Prespecified overlap or effective sample size warning")
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(reps):
        try:
            value, _ = estimator(resample(d, rng), outcome)
            if np.isfinite(value):
                values.append(value)
        except (ValueError, np.linalg.LinAlgError):
            continue
    result.update(attempted=reps, successful=len(values), failed=reps-len(values))
    if len(values) < math.ceil(.95*reps):
        return dict(result, unavailable="More than 5% bootstrap fits failed")
    try:
        test = centered_test(estimate, values)
    except ValueError as exc:
        return dict(result, unavailable=str(exc))
    return dict(result, candidate_available=True, candidate_p=test["p"],
                candidate_ci=test["ci"])


def candidate_family(d, reps=999, seed=20261127):
    seeds = np.random.SeedSequence(seed).spawn(len(MODELS))
    results = {h: candidate_test(d, outcome, "target_status2" if h == "H1" else "target_status1", reps, s)
               for (h, (outcome, _)), s in zip(MODELS.items(), seeds)}
    return {"hypotheses": results, "candidate_secondary_holm": holm(
        {h: results[h].get("candidate_p") for h in ("H2", "H3")}),
        "confirmatory_available": False}


if __name__ == "__main__":
    from allocation import reconcile
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv")
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--reps", type=int, default=999)
    parser.add_argument("--seed", type=int, default=20261127)
    args = parser.parse_args()
    from export_schema import read_export
    frame=read_export(args.csv)
    reconcile(args.ledger, frame)
    print(json.dumps(candidate_family(prepare(frame), args.reps, args.seed),
                     indent=2, allow_nan=False))
