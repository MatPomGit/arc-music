"""Ordinal-item retest simulation with an exact complete-pair moment target."""
import argparse
import itertools
import json
import numpy as np
from scipy.special import ndtr
from retest import retest_domain
from retest_calibration import wilson

SCENARIOS = ("stable", "shift", "mcar", "selective")
SIZES = (60, 100, 160)
LOADINGS = np.array([.50, .60, .70, .75, .80])
OFFSETS = np.array([-.35, -.15, 0., .20, .40])
THRESHOLDS = np.array([-1.2, -.4, .4, 1.2])
STATES = np.arange(5.) - 2
MARGINAL = np.array([.1, .2, .4, .2, .1])


def design(scenario):
    if scenario not in SCENARIOS:
        raise ValueError("unknown scenario")
    joint = .7*np.diag(MARGINAL) + .3*np.outer(MARGINAL, MARGINAL)
    shift = .65 if scenario == "shift" else 0.
    probs = []
    for offset in (0., shift):
        mean = STATES[:, None]*LOADINGS + OFFSETS + offset
        cuts = ndtr((THRESHOLDS[None, None, :]-mean[:, :, None]) /
                    np.sqrt(1-LOADINGS**2)[None, :, None])
        probs.append(np.diff(np.concatenate([np.zeros((5, 5, 1)), cuts,
                                             np.ones((5, 5, 1))], axis=2), axis=2))
    missing = np.zeros((2, 5, 5))
    follow = np.full(5, .8)
    if scenario == "mcar":
        missing[:] = .20
    elif scenario == "selective":
        follow = np.array([.45, .60, .75, .85, .95])
        missing[:] = np.linspace(.25, .05, 5)[None, :, None]
        missing[1] += .05
    return joint, np.asarray(probs), missing, follow


def occasion_moments(probs, missing):
    """Exact eligibility probability and first two score moments given state.

    Independent item errors and missing indicators conditional on state;
    average only masks with at least four of five observed items.
    """
    categories = np.arange(5.)
    means = probs @ categories
    variances = probs @ (categories**2) - means**2
    mass, first, second = [np.zeros(5) for _ in range(3)]
    for pattern in itertools.product((False, True), repeat=5):
        keep = np.asarray(pattern)
        count = int(keep.sum())
        if count < 4:
            continue
        w = np.prod(np.where(keep, 1-missing, missing), axis=1)
        mu = means[:, keep].mean(axis=1)
        var = variances[:, keep].sum(axis=1)/count**2
        mass += w
        first += w*mu
        second += w*(var+mu**2)
    if np.any(mass <= 0):
        raise ValueError("undefined conditional score moments")
    return mass, first/mass, second/mass


def target(joint, probs, missing, follow):
    a, mx, x2 = occasion_moments(probs[0], missing[0])
    b, my, y2 = occasion_moments(probs[1], missing[1])
    w = joint * (a*follow)[:, None] * b[None, :]
    retention = float(w.sum())
    if retention <= 0:
        raise ValueError("no eligible pairs")
    w /= retention
    ex, ey = np.sum(w*mx[:, None]), np.sum(w*my[None, :])
    ex2, ey2 = np.sum(w*x2[:, None]), np.sum(w*y2[None, :])
    exy = np.sum(w*mx[:, None]*my[None, :])
    den = ex2 + ey2 - 2*ex*ey
    if den <= 0:
        raise ValueError("undefined target agreement")
    return float(2*(exy-ex*ey)/den), retention


def draw_items(rng, states, probs, missing):
    cumulative = np.cumsum(probs[states], axis=2)
    x = (rng.random((len(states), 5, 1)) > cumulative[:, :, :-1]).sum(axis=2).astype(float)
    x[rng.random(x.shape) < missing[states]] = np.nan
    return x


def simulate(n, scenario, reps, boot, seed):
    if n < 2 or reps < 1 or boot < 20:
        raise ValueError("invalid simulation settings")
    joint, probs, missing, follow = design(scenario)
    truth, retention = target(joint, probs, missing, follow)
    full_truth, _ = target(joint, probs, np.zeros_like(missing), np.ones(5))
    rng = np.random.default_rng(seed)
    estimates, widths, counts = [], [], []
    covered = 0
    for _ in range(reps):
        draw = rng.choice(25, n, p=joint.ravel())
        x, y = draw//5, draw%5
        a = draw_items(rng, x, probs[0], missing[0])
        b = draw_items(rng, y, probs[1], missing[1])
        follow_up = rng.random(n) < follow[x]
        rows, records = [], []
        for i in range(n):
            person = f"s{i}"
            for stage, items, lag in (("cfa", a[i], None), ("retest", b[i], 10)):
                if stage == "retest" and not follow_up[i]:
                    continue
                rows.append(dict(participant_code=person, episode_code="e",
                                 stage=stage, lag_days=lag))
                records.append(((person, stage, "e"), items))
        out = retest_domain(rows, records, authorized=True, reps=boot,
                            seed=int(rng.integers(2**32)), min_pairs=30)
        counts.append(out["complete_pairs"])
        if "icc" in out:
            estimates.append(out["icc"])
        if out["status"] == "estimated":
            lo, hi = out["icc_interval"]
            widths.append(hi-lo)
            covered += int(lo <= truth <= hi)
    available = len(widths)
    return dict(scenario=scenario, invited=n, requested=reps, boot=boot, seed=seed,
                full_data_target=full_truth, complete_pair_target=truth,
                retention_probability=retention, mean_pairs=float(np.mean(counts)),
                point_available=len(estimates), intervals_available=available,
                covered=covered, conditional_coverage=covered/available if available else None,
                conditional_coverage_ci=wilson(covered, available),
                operational_coverage=covered/reps, operational_coverage_ci=wilson(covered, reps),
                interval_availability_ci=wilson(available, reps),
                bias=float(np.mean(estimates)-truth) if estimates else None,
                mean_width=float(np.mean(widths)) if widths else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reps", type=int, default=20)
    parser.add_argument("--boot", type=int, default=199)
    parser.add_argument("--seed", type=int, default=20261129)
    parser.add_argument("--n", type=int, choices=SIZES, nargs="+", default=list(SIZES))
    parser.add_argument("--scenario", choices=SCENARIOS, nargs="+", default=list(SCENARIOS))
    args = parser.parse_args()
    cells = [simulate(n, scenario, args.reps, args.boot,
                      int(np.random.SeedSequence([args.seed, SCENARIOS.index(scenario), n])
                          .generate_state(1)[0]))
             for scenario in args.scenario for n in args.n]
    print(json.dumps({"synthetic_only": True, "sample_size_authorized": False,
                      "cells": cells}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
