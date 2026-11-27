"""P03 prespecified complete-record models. No participant data bundled."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from intake import select, read_records

MOTIVES = ["motive_expression", "motive_mood", "motive_explore", "motive_fun"]
BACKGROUND = ["age", "experience", "use_days", "recency", "source"]
OPS = ["regenerated", "selected", "edited"]
SOURCES = ("university", "community", "other")
RANGES = {k: (0, 10) for k in MOTIVES + [
    "experience", "clarity_pre", "clarity_post", "valence_pre", "valence_post",
    "agency", "resonance", "function_expression", "function_explore",
    "function_distraction", "function_social", "frustration", "difficulty_disengaging"]}
RANGES.update({"use_days": (0, 30), "recency": (0, 30), "age": (18, np.inf)})
RANGES.update({k: (0, 1) for k in OPS + ["prompted"]})
INTEGERS = set(OPS + ["prompted", "age", "use_days", "recency"])
MODELS = {
    "H1": ("clarity_post", "motive_expression", ["clarity_pre"] + MOTIVES + BACKGROUND),
    "H2": ("valence_post", "motive_mood", ["valence_pre"] + MOTIVES + BACKGROUND),
    "H3": ("iteration_count", "motive_explore", MOTIVES + BACKGROUND),
    "H4": ("resonance", "agency", ["agency"] + MOTIVES + BACKGROUND),
}


def prepare(raw):
    """Filter consent/eligibility; convert invalid observations to missing, not zero."""
    required = {"study_id", "consent", "eligible", *MOTIVES, *BACKGROUND, *OPS,
                "clarity_pre", "clarity_post", "valence_pre", "valence_post", "agency", "resonance"}
    absent = required - set(raw.columns)
    if absent:
        raise ValueError(f"Missing columns: {sorted(absent)}")
    data = select(raw)
    invalid = {}
    for key, (lo, hi) in RANGES.items():
        if key not in data:
            continue
        x = pd.to_numeric(data[key], errors="coerce")
        valid = np.isfinite(x) & x.between(lo, hi)
        if key in INTEGERS:
            valid &= x.mod(1).eq(0)
        invalid[key] = int((data[key].notna() & ~valid).sum())
        data[key] = x.where(valid)
    valid = data.source.isin(SOURCES)
    invalid["source"] = int((data.source.notna() & ~valid).sum())
    data["source"] = data.source.where(valid)
    data["iteration_count"] = data[OPS].sum(axis=1, min_count=len(OPS))
    return data, invalid


def design(data, hypothesis):
    outcome, target, predictors = MODELS[hypothesis]
    rows = data[[outcome] + predictors].dropna()
    x = rows[predictors].drop(columns="source").astype(float)
    for category in SOURCES[1:]:
        x["source_" + category] = rows.source.eq(category).astype(float)
    x = sm.add_constant(x, has_constant="add")
    y = rows[outcome].astype(float)
    if len(y) <= x.shape[1] or np.linalg.matrix_rank(x) < x.shape[1]:
        raise ValueError(f"{hypothesis}: insufficient observations or rank-deficient design")
    return y, x, target


def fit(data, hypothesis):
    y, x, target = design(data, hypothesis)
    model = sm.OLS(y, x).fit(cov_type="HC3", use_t=True)
    lo, hi = model.conf_int().loc[target]
    # Partial correlation uses classical residualization, not robust t conversion.
    z = x.drop(columns=target)
    ry = sm.OLS(y, z).fit().resid
    rx = sm.OLS(x[target], z).fit().resid
    partial = float(np.corrcoef(ry, rx)[0, 1])
    if not np.isfinite([model.params[target], model.bse[target], model.pvalues[target], partial, lo, hi]).all():
        raise ValueError(f"{hypothesis}: nonfinite inference")
    return {"n": len(y), "beta": float(model.params[target]),
            "se_hc3": float(model.bse[target]), "ci95": [float(lo), float(hi)],
            "p": float(model.pvalues[target]), "partial_r": partial}


def analyze(raw):
    data, invalid = prepare(raw)
    results = {}
    for h in MODELS:
        try:
            results[h] = fit(data, h)
        except ValueError as exc:
            results[h] = {"error": str(exc)}
    # Preserve the three-test family: failed tests contribute p=1, not a smaller family.
    secondary = ["H2", "H3", "H4"]
    adjusted = multipletests([results[h].get("p", 1.0) for h in secondary], method="holm")[1]
    for h, p in zip(secondary, adjusted):
        if "p" in results[h]:
            results[h]["p_holm"] = float(p)
    return {"eligible_n": len(data), "submitted_n": len(raw), "intake_flow": data.attrs["intake_flow"], "invalid": invalid,
            "missing": {k: int(v) for k, v in data.isna().sum().items() if k != "study_id"},
            "models": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--data-kind", choices=["synthetic", "empirical"], required=True)
    args = parser.parse_args()
    result = analyze(read_records(args.csv))
    result["data_kind"] = args.data_kind
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
