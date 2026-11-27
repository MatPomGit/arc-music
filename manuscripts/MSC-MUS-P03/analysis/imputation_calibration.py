"""Prospective calibration of the production P03 H1 imputation and stopping rule.

Synthetic records only. The rounded full-data projection is estimated independently.
Compare complete records, zero-shift PMM and two differential MNAR sensitivity
scenarios using the same imputations. This screen is not validation of all 17 shifts.
"""
import argparse
import json
from itertools import product

import numpy as np
import pandas as pd

from imputation import draw_imputations, pool, shift_outcome
from models import MODELS, fit, prepare
from power import calibration, wilson
from scipy.special import expit
from scipy.stats import binom
from stress import generate

MECHANISMS = ("complete", "outcome_mar", "predictor_mar", "mixed_mar", "outcome_mnar")
SHIFTS = {"mi_zero": (0, 0), "mi_slope_minus2": (0, -2), "mi_slope_plus2": (0, 2)}
CORE = [MODELS["H1"][0], *MODELS["H1"][2]]


def raw_records(x, y):
    """Match the production schema without inventing predictive auxiliary variables."""
    return pd.DataFrame(dict(
        study_id=[f"p03-00000000-0000-4000-8000-{i:012x}" for i in range(len(y))], consent=True, eligible=True,
        motive_expression=x[:, 1], motive_mood=x[:, 2],
        motive_explore=x[:, 3], motive_fun=x[:, 4], clarity_pre=x[:, 5],
        age=x[:, 6], experience=x[:, 7], use_days=x[:, 8], recency=x[:, 9],
        source=np.where(x[:, 10] == 1, "community",
                        np.where(x[:, 11] == 1, "other", "university")),
        clarity_post=y, valence_pre=np.nan, valence_post=np.nan, agency=np.nan,
        resonance=np.nan, regenerated=np.nan, selected=np.nan, edited=np.nan))


def mask_and_stop(rng, raw, mechanism, target):
    """Keep all submissions before reaching the complete-record target or cap."""
    if mechanism not in MECHANISMS or not 1 <= target <= len(raw):
        raise ValueError("Invalid mechanism or target")
    raw = raw.copy()
    pre = raw.clarity_pre.to_numpy() - 5
    x = raw.motive_expression.to_numpy() - 5
    y = raw.clarity_post.to_numpy() - 5
    outcome = np.zeros(len(raw))
    predictor = np.zeros(len(raw))
    if mechanism == "outcome_mar":
        outcome = expit(-2.2 + .12*x - .16*pre)
    elif mechanism == "predictor_mar":
        predictor = expit(-1.9 + .20*y + .10*pre)
    elif mechanism == "mixed_mar":
        # Both masks depend only on the always-observed baseline score.
        outcome = expit(-2.2 - .16*pre)
        predictor = expit(-2.2 + .16*pre)
    elif mechanism == "outcome_mnar":
        outcome = expit(-1.9 - .25*y + .15*x*y)
    raw.loc[rng.random(len(raw)) < outcome, "clarity_post"] = np.nan
    raw.loc[rng.random(len(raw)) < predictor, "motive_expression"] = np.nan
    data, _ = prepare(raw)
    complete = data[CORE].notna().all(axis=1).to_numpy()
    ids = np.flatnonzero(complete)
    stop = ids[target-1]+1 if len(ids) >= target else len(data)
    return data.iloc[:stop].reset_index(drop=True), int(complete[:stop].sum())


def estimates(data, m, sweeps, seed):
    """Refit the production estimator for each shared imputation and scenario."""
    output = {}
    try:
        output["complete_case"] = fit(data, "H1")
    except (ValueError, np.linalg.LinAlgError):
        output["complete_case"] = None
    samples = {key: [] for key in SHIFTS}
    try:
        for completed, missing in draw_imputations(data, m, sweeps, seed):
            for key, (delta, slope) in SHIFTS.items():
                samples[key].append(fit(shift_outcome(completed, missing, delta, slope), "H1"))
    except (ValueError, np.linalg.LinAlgError):
        pass
    for key, results in samples.items():
        try:
            output[key] = pool(results) if len(results) == m else None
        except (ValueError, np.linalg.LinAlgError):
            output[key] = None
    return output


def summary(values, truth):
    n = len(values)
    good = [v for v in values if v is not None]
    k = len(good)
    out = dict(attempted=n, fitted=k, failures=n-k)
    if not k:
        return out | dict(bias=None, rmse=None, coverage=None, rejection=None,
                          operational_coverage=0., operational_rejection=0.,
                          coverage_mcse=None, rejection_mcse=None)
    b = np.array([v["beta"] for v in good])
    covered = sum(v["ci95"][0] <= truth <= v["ci95"][1] for v in good)
    rejected = sum(v["p"] < .05 for v in good)
    c, r = covered/k, rejected/k
    out.update(bias=float(b.mean()-truth), rmse=float(np.sqrt(((b-truth)**2).mean())),
               bias_mcse=float(b.std(ddof=1)/np.sqrt(k)) if k > 1 else None,
               coverage=c, rejection=r, coverage_ci95=wilson(covered,k),
               rejection_ci95=wilson(rejected,k),
               coverage_mcse=float(np.sqrt(c*(1-c)/k)),
               rejection_mcse=float(np.sqrt(r*(1-r)/k)),
               operational_coverage=covered/n, operational_rejection=rejected/n)
    return out


def mixed_mar_attainment(target=500, caps=(640, 660, 680, 700)):
    """Exact retention sensitivity for the rounded mixed-MAR synthetic model."""
    if target < 1 or any(cap < target for cap in caps):
        raise ValueError("Invalid target or cap")
    pre = np.arange(11, dtype=float) - 5
    mass = np.full(11, .10)
    mass[[0, -1]] = .05
    complete = float(mass @ ((1-expit(-2.2-.16*pre)) *
                             (1-expit(-2.2+.16*pre))))
    return dict(p_complete=complete, target=target,
                caps=[dict(cap=cap, expected_complete=cap*complete,
                           attainment=float(binom.sf(target-1, cap, complete)))
                      for cap in caps],
                assumptions="rounded uniform baseline, conditional independent masks, iid eligible submissions")


def run(mechanism, reps=30, m=10, sweeps=5, target=500, cap=640,
        seed=20261127, reference_n=500000, rounded=True, *, effect_override=None):
    if mechanism not in MECHANISMS or reps < 2 or not 50 <= target <= cap:
        raise ValueError("Invalid design")
    if m < 2 or sweeps < 1 or reference_n < 1000:
        raise ValueError("Invalid imputation or reference settings")
    cells = []
    if effect_override is not None and not 0<=effect_override<=.6:raise ValueError('Invalid partial correlation')
    for effect in ((0., .15) if effect_override is None else (effect_override,)):
        beta = calibration(.6, effect)
        ref_rng = np.random.default_rng(np.random.SeedSequence([seed, 99, int(effect*100)]))
        if rounded:
            x, y = generate(ref_rng, reference_n, .6, beta, True)
            truth = float(np.linalg.lstsq(x, y, rcond=None)[0][1])
        else:
            truth = float(beta)
        rng = np.random.default_rng(np.random.SeedSequence(
            [seed, MECHANISMS.index(mechanism), int(effect*100), int(rounded)]))
        values = {key: [] for key in ("complete_case", *SHIFTS)}
        flow = []
        for _ in range(reps):
            x, y = generate(rng, cap, .6, beta, rounded)
            data, complete = mask_and_stop(rng, raw_records(x, y), mechanism, target)
            flow.append([len(data), complete, data.clarity_post.isna().sum(),
                         data.motive_expression.isna().sum()])
            result = estimates(data, m, sweeps, int(rng.integers(0, 2**32)))
            for key, value in result.items():
                values[key].append(value)
        f = np.array(flow)
        cells.append(dict(partial_r_input=effect, projection_reference=truth,
                          reference_kind="estimated_rounded_projection" if rounded else "exact_continuous",
                          mean_submitted=float(f[:,0].mean()), mean_complete=float(f[:,1].mean()),
                          attainment=float((f[:,1]==target).mean()),
                          mean_missing_outcome=float(f[:,2].mean()),
                          mean_missing_predictor=float(f[:,3].mean()),
                          methods={key: summary(v, truth) for key,v in values.items()}))
    return dict(synthetic=True, mechanism=mechanism, target_complete=target, cap=cap,
                reps=reps, m=m, sweeps=sweeps, seed=seed, rounded=rounded,
                reference_n=reference_n, screening_only=True, cells=cells,
                exact_rounded_mixed_mar_retention=mixed_mar_attainment(target, (cap, max(cap, 660)))
                if rounded and mechanism == "mixed_mar" else None)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mechanism", choices=MECHANISMS, required=True)
    p.add_argument("--reps", type=int, default=30)
    p.add_argument("--m", type=int, default=10)
    p.add_argument("--sweeps", type=int, default=5)
    p.add_argument("--target", type=int, default=500)
    p.add_argument("--cap", type=int, default=640)
    p.add_argument("--seed", type=int, default=20261127)
    p.add_argument("--reference-n", type=int, default=500000)
    p.add_argument("--continuous", action="store_true")
    p.add_argument("--effect",type=float)
    a = p.parse_args()
    print(json.dumps(run(a.mechanism, a.reps, a.m, a.sweeps, a.target, a.cap,
                         a.seed, a.reference_n, not a.continuous, effect_override=a.effect), indent=2, allow_nan=False))
