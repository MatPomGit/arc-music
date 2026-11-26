"""P06 primary within-person association; prospective, no clinical inference."""
import argparse
import json
from datetime import datetime
import numpy as np
import pandas as pd
from scipy.stats import t

PREDICTORS = ["avoidance", "distress_pre", "expected_difficulty", "study_day"]
SCORES = PREDICTORS[:3] + ["interference"]

def eligible_rows(frame):
    required = {"participant_id", "session_id", "local_day", "eligible_first",
                "activity_defined", "pre_time", "post_time", "followup_time",
                *PREDICTORS, "interference"}
    if not required <= set(frame):
        raise ValueError(f"Missing columns: {sorted(required - set(frame))}")
    d = frame.copy()
    if d[["participant_id", "session_id"]].isna().any().any() or d["session_id"].duplicated().any():
        raise ValueError("Missing or duplicate identifiers")
    for flag in ["eligible_first", "activity_defined"]:
        if not d[flag].isin([True, False]).all():
            raise ValueError(f"Invalid flag: {flag}")
    d = d[d["eligible_first"] & d["activity_defined"]].copy()
    if d.duplicated(["participant_id", "local_day"]).any():
        raise ValueError("More than one eligible session per day")
    for col in SCORES + ["study_day"]:
        values = pd.to_numeric(d[col], errors="raise")
        lo, hi = (1, 14) if col == "study_day" else (0, 10)
        nonnull = values.dropna()
        if not (nonnull.between(lo, hi) & (nonnull % 1 == 0)).all():
            raise ValueError(f"Invalid score: {col}")
        d[col] = values
    def parse(value):
        if pd.isna(value):
            return pd.NaT
        x = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if x.utcoffset() is None:
            raise ValueError("Timezone offset required")
        return pd.Timestamp(x).tz_convert("UTC")
    for col in ["pre_time", "post_time", "followup_time"]:
        d[col] = pd.to_datetime(d[col].map(parse), utc=True)
    # Follow-up target is measured relative to the end of the session.
    post_delay = (d["post_time"] - d["pre_time"]).dt.total_seconds()/3600
    follow = (d["followup_time"] - d["post_time"]).dt.total_seconds()/3600
    valid = (post_delay >= 0) & follow.between(20, 28)
    return d.loc[valid].dropna(subset=PREDICTORS + ["interference"]).copy()

def fit_arrays(group, x, y):
    group = np.asarray(group)
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim != 2 or y.ndim != 1 or group.ndim != 1 or len(group) != len(y) or len(x) != len(y):
        raise ValueError("Incompatible input dimensions")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Nonfinite input")
    _, g = np.unique(group, return_inverse=True)
    counts = np.bincount(g)
    keep = counts[g] >= 2
    x, y, g = x[keep], y[keep], g[keep]
    _, g = np.unique(g, return_inverse=True)
    counts = np.bincount(g)
    G, N, p = len(counts), len(y), x.shape[1]
    if G < 10 or N - G - p <= 0:
        raise ValueError("Insufficient independent participants or residual degrees of freedom")
    xm = np.zeros((G,p)); ym = np.zeros(G)
    np.add.at(xm,g,x); np.add.at(ym,g,y)
    x = x - xm[g]/counts[g,None]
    y = y - ym[g]/counts[g]
    if np.linalg.matrix_rank(x) < p:
        raise ValueError("Within-person design is rank deficient")
    bread = np.linalg.inv(x.T @ x)
    beta = bread @ x.T @ y
    resid = y - x @ beta
    scores = np.zeros((G,p))
    np.add.at(scores,g,x*resid[:,None])
    # Cluster CR1 with absorbed participant intercepts counted in model df.
    cov = (G/(G-1))*((N-1)/(N-G-p))*bread @ (scores.T @ scores) @ bread
    se = np.sqrt(np.maximum(np.diag(cov),0))
    if (se <= 0).any():
        raise ValueError("Degenerate cluster uncertainty")
    critical = t.ppf(.975,G-1)
    return {"participants":G,"sessions":N,"df":G-1,
            "estimate":beta.tolist(),"se":se.tolist(),
            "ci_low":(beta-critical*se).tolist(),"ci_high":(beta+critical*se).tolist(),
            "p":(2*t.sf(np.abs(beta/se),G-1)).tolist()}

def primary(frame):
    d = eligible_rows(frame)
    result = fit_arrays(d.participant_id, d[PREDICTORS], d.interference)
    return {"predictors":PREDICTORS, "input_rows":len(frame),
            "eligible_complete_rows_before_singleton_filter":len(d), **result}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    args = parser.parse_args()
    print(json.dumps(primary(pd.read_csv(args.csv)),indent=2,allow_nan=False))
