"""Synthetic calibration of the P09 production HC3 estimators (A01.4)."""
import argparse
import itertools
import json

import numpy as np
import pandas as pd
from scipy.special import expit
from inference import MODELS, design, fit_arrays, holm

# Baseline probability, follow-up control centre, slope, concentration by arm.
PROFILES = {
    "standard": (.50, .50, .65, 20., 20.),
    "weak_baseline": (.50, .50, .15, 20., 20.),
    "ceiling": (.80, .76, .65, 20., 20.),
    "heteroskedastic": (.50, .50, .65, 30., 5.),
}
MECHANISMS = ("complete", "MCAR", "MAR", "MNAR")
EFFECTS = {"null": (0., 0., 0.), "alternative": (.5, .5, 0.)}
STRESS_EFFECTS = {"distance_only": (0., 0., .5), "all_positive": (.5, .5, .5)}
STRESS_MECHANISMS = ("MAR_nonlinear", "MAR_low_overlap")


def effect_values(name):
    return (EFFECTS | STRESS_EFFECTS)[name]


def rating(rng, probability, concentration, items):
    """Mean of integer 0--10 ratings; shared beta propensity induces dependence."""
    probability = np.asarray(probability)
    if np.any((probability <= 0) | (probability >= 1)):
        raise ValueError("Invalid generating probability")
    latent = rng.beta(probability * concentration, (1 - probability) * concentration)
    return rng.binomial(10, latent[:, None], size=(len(latent), items)).mean(axis=1)


def observed(rng, mechanism, arm, baseline, outcome, centre):
    if mechanism == "complete":
        return np.ones(len(arm), dtype=bool)
    logit = np.full(len(arm), np.log(4.))
    if mechanism in ("MAR", "MNAR"):
        logit += .35 * (baseline - centre) - .55 * arm
    if mechanism == "MNAR":
        logit += .45 * (outcome - centre)
    if mechanism == "MAR_nonlinear":
        logit += -.65 * (baseline - centre)**2 + .75 * arm * (baseline - centre)
    if mechanism == "MAR_low_overlap":
        logit = 1.0 + 2.5 * (baseline - centre) - 1.5 * arm
    return rng.random(len(arm)) < expit(logit)


def stratified_assignment(rng, training):
    """Simulate sequential concealed blocks of 4 or 6 within each stratum."""
    training = np.asarray(training)
    if training.ndim != 1 or not np.isin(training, (0, 1)).all():
        raise ValueError("Invalid training stratum")
    assignment = np.empty(len(training), dtype=int)
    for stratum in (0, 1):
        positions = np.flatnonzero(training == stratum)
        offset = 0
        while offset < len(positions):
            block = np.tile([0, 1], int(rng.choice((2, 3))))
            rng.shuffle(block)
            used = min(len(block), len(positions) - offset)
            assignment[positions[offset:offset+used]] = block[:used]
            offset += used
    return assignment


def generate(rng, n, profile, mechanism, alternative, *, allocation="balanced"):
    if n < 20 or n % 2:
        raise ValueError("n must be even and at least 20")
    if mechanism not in MECHANISMS + STRESS_MECHANISMS:
        raise ValueError("Unknown missingness mechanism")
    base_p, centre, slope, c0, c1 = PROFILES[profile]
    effects = effect_values(alternative)
    if allocation == "balanced":
        z = np.repeat([0, 1], n // 2)
        rng.shuffle(z)
        training = None
    elif allocation == "stratified_blocks":
        training = rng.binomial(1, .4, n)
        z = stratified_assignment(rng, training)
    else:
        raise ValueError("Unknown allocation design")
    base = rating(rng, np.full(n, base_p), 15., 3)
    distance = rating(rng, np.full(n, .5), 15., 1)
    concentration = np.where(z == 0, c0, c1)
    p = centre + slope * (base / 10 - base_p)
    y2 = rating(rng, p + z * effects[0] / 10, concentration, 3)
    y1 = rating(rng, p + z * effects[1] / 10, concentration, 3)
    d1 = rating(rng, .5 + .55 * (distance / 10 - .5) + z * effects[2] / 10,
                concentration, 1)
    # T1 outcomes share a visit-level observation indicator. MNAR depends on
    # the latent complete T1 understanding score; H3 is not assumed MAR.
    keep1 = observed(rng, mechanism, z, base, y1, base_p * 10)
    keep2 = observed(rng, mechanism, z, base, y2, base_p * 10)
    return pd.DataFrame(dict(
        music=z, training=rng.binomial(1, .4, n) if training is None else training,
        importance0=rng.integers(0, 11, n), prior_use_days=rng.integers(0, 31, n),
        understanding0=base, distance0=distance,
        understanding2=np.where(keep2, y2, np.nan),
        understanding1=np.where(keep1, y1, np.nan),
        distance1=np.where(keep1, d1, np.nan),
    ))


def proportion(values):
    if not values:
        return {"rate": None, "mcse": None, "denominator": 0}
    p = float(np.mean(values))
    return {"rate": p, "mcse": float(np.sqrt(p * (1 - p) / len(values))),
            "denominator": len(values)}


def summarize(results, truth, reps):
    beta = np.array([x["beta"] for x in results])
    success = len(beta)
    return dict(
        truth=truth, attempted=reps, fitted=success, failures=reps-success,
        bias=float(beta.mean()-truth) if success else None,
        bias_mcse=float(beta.std(ddof=1)/np.sqrt(success)) if success > 1 else None,
        rmse=float(np.sqrt(np.mean((beta-truth)**2))) if success else None,
        coverage=proportion([x["ci"][0] <= truth <= x["ci"][1] for x in results]),
        rejection=proportion([x["p"] < .05 for x in results]),
        # Missing fits count as non-rejections only in this operational metric.
        operational_rejection=proportion([x["p"] < .05 for x in results]
                                         + [False] * (reps-success)),
        mean_n=float(np.mean([x["n"] for x in results])) if success else None,
    )


def cell(seed, n, profile, mechanism, alternative, reps, *, allocation="balanced"):
    rng = np.random.default_rng(seed)
    fits = {h: [] for h in MODELS}
    holm_rates = {h: [] for h in ("H2", "H3")}
    fwer = []
    observed_arm = {h: [[], []] for h in MODELS}
    truth = dict(zip(MODELS, effect_values(alternative)))
    for _ in range(reps):
        d = generate(rng, n, profile, mechanism, alternative, allocation=allocation)
        secondary = {}
        for h, (outcome, baseline) in MODELS.items():
            for a in (0, 1):
                observed_arm[h][a].append(float(d.loc[d.music == a, outcome].notna().mean()))
            complete = d[d[outcome].notna()]
            try:
                result = fit_arrays(design(complete, baseline), complete[outcome].to_numpy(float))
            except (ValueError, np.linalg.LinAlgError):
                result = None
            if result is not None:
                fits[h].append(result)
            if h != "H1":
                secondary[h] = None if result is None else result["p"]
        adjusted = holm(secondary)
        for h in holm_rates:
            holm_rates[h].append(adjusted[h] is not None and adjusted[h] < .05)
        fwer.append(any(holm_rates[h][-1] for h in holm_rates if truth[h] == 0))
    return dict(n=n, profile=profile, missingness=mechanism, effect=alternative, allocation=allocation,
                hypotheses={h: dict(summarize(fits[h], truth[h], reps),
                                    observed_arm=[float(np.mean(x)) for x in observed_arm[h]])
                            for h in MODELS},
                secondary_holm={h: proportion(v) for h, v in holm_rates.items()},
                secondary_false_rejection=proportion(fwer))


def run(seed, reps, smoke=False):
    if reps < 2:
        raise ValueError("At least two replications required")
    grid = list(itertools.product(
        (588,) if smoke else (434, 588),
        ("standard",) if smoke else PROFILES,
        ("complete", "MNAR") if smoke else MECHANISMS,
        EFFECTS,
    ))
    seeds = np.random.SeedSequence(seed).spawn(len(grid))
    return dict(schema_version=1, synthetic=True, seed=seed, reps_per_cell=reps,
                target="superpopulation assignment contrast in original scale points",
                cells=[cell(s, *g, reps) for s, g in zip(seeds, grid)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261127)
    parser.add_argument("--reps", type=int, default=200)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.seed, args.reps, args.smoke), indent=2, allow_nan=False))
