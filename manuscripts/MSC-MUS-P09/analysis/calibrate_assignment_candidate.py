"""Calibrate the actual defined-outcome development candidate and family gate."""
import argparse
import itertools
import json
import numpy as np
from calibration import generate, effect_values, proportion
from assignment_candidate import candidate_family
from inference import MODELS


def cell(seed, n, mechanism, effect, reps, draws, profile):
    rng = np.random.default_rng(seed)
    truth = dict(zip(MODELS, effect_values(effect)))
    records = {h: [] for h in MODELS}
    fwer = []
    for _ in range(reps):
        d = generate(rng, n, profile, mechanism, effect, allocation="stratified_blocks")
        d["target_status1"] = d["target_status2"] = "defined"
        report = candidate_family(d, reps=draws, seed=int(rng.integers(0, 2**32)))
        for h, row in report["hypotheses"].items():
            records[h].append(row)
        fwer.append(any(p is not None and p <= .05 for h, p in
                        report["candidate_secondary_holm"].items() if truth[h] == 0))
    result = {}
    for h, rows in records.items():
        errors = np.array([x["contrast"]-truth[h] for x in rows if "contrast" in x])
        valid = [x for x in rows if x["candidate_available"]]
        covered = [x["candidate_ci"][0] <= truth[h] <= x["candidate_ci"][1] for x in valid]
        rejected = [x["candidate_p"] <= .05 for x in valid]
        result[h] = {
            "truth": truth[h], "requested": reps, "point_fits": len(errors),
            "candidate_available": len(valid), "unavailable": reps-len(valid),
            "unavailable_reasons": {reason: sum(x.get("unavailable")==reason for x in rows)
                                    for reason in sorted({x["unavailable"] for x in rows if "unavailable" in x})},
            "bias": float(errors.mean()) if len(errors) else None,
            "bias_mcse": float(errors.std(ddof=1)/np.sqrt(len(errors))) if len(errors)>1 else None,
            "rmse": float(np.sqrt(np.mean(errors**2))) if len(errors) else None,
            "conditional_coverage": proportion(covered),
            "operational_coverage": proportion(covered+[False]*(reps-len(valid))),
            "conditional_rejection": proportion(rejected),
            "operational_rejection": proportion(rejected+[False]*(reps-len(valid))),
            "bootstrap_successful": sum(x["successful"] for x in rows),
            "bootstrap_failed": sum(x["failed"] for x in rows),
        }
    return {"mechanism": mechanism, "effect": effect, "profile": profile, "n": n,
            "hypotheses": result, "secondary_true_null_fwer": proportion(fwer)}


def run(seed, n, reps, draws, smoke=False):
    if reps < 2:
        raise ValueError("At least two independent datasets per cell")
    grid = list(itertools.product(("complete", "MCAR", "MAR", "MNAR"),
                                  ("null", "all_positive", "distance_only"), ("standard",)))
    if smoke:
        grid = [("MCAR", "null", "standard"), ("MAR", "all_positive", "standard")]
    else:
        grid += list(itertools.product(("MAR_nonlinear", "MAR_low_overlap"),
                                       ("null", "all_positive"), ("standard", "ceiling")))
    seeds = np.random.SeedSequence(seed).spawn(len(grid))
    return {"synthetic": True, "purpose": "development screening, not authorization",
            "seed": seed, "outer_reps": reps, "bootstrap_draws": draws,
            "cells": [cell(s, n, m, e, reps, draws, p) for s,(m,e,p) in zip(seeds,grid)]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261129)
    parser.add_argument("--n", type=int, default=600)
    parser.add_argument("--reps", type=int, default=20)
    parser.add_argument("--draws", type=int, default=199)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.seed,args.n,args.reps,args.draws,args.smoke),indent=2,allow_nan=False))
