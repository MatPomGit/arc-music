"""Calibrate percentile intervals on synthetic heard records at the authority null."""
import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from itertools import product

import numpy as np
import pandas as pd

from inference import BASE
from sensitivity import bootstrap
from simulation import draw


def calibrate_replication(entry):
    mechanism, draws, seed = entry
    rng = np.random.default_rng(seed)
    x, y, observed = draw(rng, 240, 0., 0., mechanism, nonadherence=.15)
    # Hearing depends on execution and baseline, but not authority. At the
    # joint null the full synthetic heard population has a zero A contrast.
    heard = rng.random(len(x)) >= np.where(x[:, 2] > 0, .10, .05)
    frame = pd.DataFrame(x[:, 4:], columns=BASE)
    frame["authority"] = x[:, 1] + .5
    frame["manual"] = x[:, 2] + .5
    frame["heard_version"] = heard
    frame["ownership"] = np.where(heard & observed[0], y[0], np.nan)
    result = bootstrap(frame, "ownership", draws, seed)
    if "unavailable" in result:
        return None
    return [
        result["ipw"]["20"]["authority"],
        result["shift"]["0/0/0"]["authority"],
    ]


def run(reps, draws, seed, jobs):
    result = {}
    for mechanism in ("mar", "mnar"):
        seeds = np.random.SeedSequence(seed).generate_state(reps)
        cells = list(product([mechanism], [draws], map(int, seeds)))
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            records = list(pool.map(calibrate_replication, cells))
        intervals = np.asarray([record for record in records if record is not None])
        valid = len(intervals)
        result[mechanism] = {"valid": valid, "failure": reps - valid}
        if valid:
            for index, name in enumerate(("ipw20", "shift_zero")):
                lo, hi = intervals[:, index, :].T
                coverage = float(np.mean((lo <= 0) & (hi >= 0)))
                result[mechanism][name] = {
                    "coverage": coverage,
                    "mcse": float(np.sqrt(coverage * (1 - coverage) / valid)),
                    "mean_width": float(np.mean(hi - lo)),
                }
    return {"status": "SYNTHETIC", "n": 240, "reps": reps, "draws": draws,
            "seed": seed, "scenarios": result}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reps", type=int, default=100)
    parser.add_argument("--draws", type=int, default=199)
    parser.add_argument("--seed", type=int, default=2809)
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()
    if args.reps < 1 or args.draws < 199 or args.jobs < 1:
        parser.error("Require positive reps/jobs and at least 199 bootstrap draws")
    print(json.dumps(run(args.reps, args.draws, args.seed, args.jobs), indent=2, allow_nan=False))
