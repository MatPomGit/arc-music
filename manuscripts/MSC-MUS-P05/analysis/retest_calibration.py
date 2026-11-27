"""Synthetic calibration of same-episode agreement, not empirical validation."""
import argparse
import json
import numpy as np
from retest import retest_domain

SCENARIOS = ("stable", "shift", "selective")
SIZES = (30, 60, 100, 160)


def distribution(scenario):
    """Joint score law and follow-up probability, both known exactly."""
    if scenario not in SCENARIOS:
        raise ValueError("unknown scenario")
    marginal = np.array([.1, .2, .4, .2, .1])
    joint = .7*np.diag(marginal) + .3*np.outer(marginal, marginal)
    if scenario != "stable":
        shifted = np.zeros_like(joint)
        for j in range(5):
            shifted[:, min(j+1, 4)] += joint[:, j]
        joint = shifted
    follow = np.array([.5, .6, .7, .8, .9]) if scenario == "selective" else np.full(5, .8)
    return joint, follow


def population_agreement(joint):
    """Population absolute-agreement functional for two occasions."""
    w = np.asarray(joint, float)
    if w.shape != (5, 5) or not np.isfinite(w).all() or (w < 0).any() or w.sum() <= 0:
        raise ValueError("invalid joint law")
    w = w/w.sum()
    x, y = np.indices(w.shape)
    mx, my = np.sum(w*x), np.sum(w*y)
    vx, vy = np.sum(w*(x-mx)**2), np.sum(w*(y-my)**2)
    cov = np.sum(w*(x-mx)*(y-my))
    den = vx + vy + (my-mx)**2
    if den <= 0:
        raise ValueError("undefined population agreement")
    return float(2*cov/den)


def wilson(k, n):
    if n == 0:
        return None
    z = 1.959963984540054
    p = k/n
    den = 1+z*z/n
    c = (p+z*z/(2*n))/den
    h = z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [float(max(0, c-h)), float(min(1, c+h))]


def simulate(n, scenario, reps, boot, seed):
    if n < 2 or reps < 1 or boot < 20:
        raise ValueError("invalid simulation settings")
    joint, follow = distribution(scenario)
    target = population_agreement(joint*follow[:, None])
    all_target = population_agreement(joint)
    rng = np.random.default_rng(seed)
    point, widths, retained = [], [], []
    covered = 0
    for _ in range(reps):
        draws = rng.choice(25, size=n, p=joint.ravel())
        x, y = draws//5, draws%5
        observed = rng.random(n) < follow[x]
        rows, records = [], []
        for i in range(n):
            person = f"s{i}"
            for stage, score, lag in (("cfa", x[i], None), ("retest", y[i], 10)):
                if stage == "retest" and not observed[i]:
                    continue
                rows.append(dict(participant_code=person, episode_code="e",
                                 stage=stage, lag_days=lag))
                # Stylised domain scores, not simulated item-level psychometrics.
                records.append(((person, stage, "e"), [int(score)]*5))
        out = retest_domain(rows, records, authorized=True, reps=boot,
                            seed=int(rng.integers(2**32)), min_pairs=30)
        retained.append(out["complete_pairs"])
        if "icc" in out:
            point.append(out["icc"])
        if out["status"] == "estimated":
            lo, hi = out["icc_interval"]
            widths.append(hi-lo)
            covered += int(lo <= target <= hi)
    available = len(widths)
    return dict(scenario=scenario, invited=n, requested=reps, boot=boot, seed=seed,
                population_icc=all_target, complete_pair_target=target,
                retention_probability=float(np.sum(joint*follow[:, None])),
                mean_pairs=float(np.mean(retained)), point_available=len(point),
                intervals_available=available, covered=covered,
                conditional_coverage=covered/available if available else None,
                conditional_coverage_ci=wilson(covered, available),
                operational_coverage=covered/reps,
                operational_coverage_ci=wilson(covered, reps),
                interval_availability_ci=wilson(available, reps),
                bias=float(np.mean(point)-target) if point else None,
                mean_width=float(np.mean(widths)) if widths else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reps", type=int, default=20)
    parser.add_argument("--boot", type=int, default=199)
    parser.add_argument("--seed", type=int, default=20261128)
    parser.add_argument("--n", type=int, choices=SIZES, nargs="+", default=list(SIZES))
    parser.add_argument("--scenario", choices=SCENARIOS, nargs="+", default=list(SCENARIOS))
    args = parser.parse_args()
    cells = []
    for scenario in args.scenario:
        for n in args.n:
            child = np.random.SeedSequence([args.seed, SCENARIOS.index(scenario), n])
            cells.append(simulate(n, scenario, args.reps, args.boot,
                                  int(child.generate_state(1)[0])))
    print(json.dumps({"synthetic_only": True, "sample_size_authorized": False,
                      "cells": cells}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
