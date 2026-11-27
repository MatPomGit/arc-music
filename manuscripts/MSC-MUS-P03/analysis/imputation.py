"""H1 multiple imputation and delta sensitivity via bootstrap donor matching."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import t
from models import prepare, fit, MODELS, SOURCES, RANGES
from intake import read_records

DELTAS = (-2, -1, 0, 1, 2)
AUX = ["valence_pre", "valence_post", "agency", "resonance", "prompted",
       "regenerated", "selected", "edited", "function_expression",
       "function_explore", "function_distraction", "function_social",
       "frustration", "difficulty_disengaging"]


def matrix(frame, columns):
    parts = [np.ones((len(frame), 1))]
    for key in columns:
        if key == "source":
            parts.append(np.column_stack([frame[key].eq(c).to_numpy(float) for c in SOURCES[1:]]))
        else:
            x = frame[key].to_numpy(float)
            parts.append(((x-x.mean())/max(x.std(), 1e-8))[:, None])
    return np.column_stack(parts)


def draw_imputations(data, m=50, sweeps=15, seed=1729, donors=5, *, trace=None):
    """Use only observed donor values; categorical source is matched on three scores."""
    if m < 2 or sweeps < 1 or donors < 1:
        raise ValueError("Require m>=2, sweeps>=1, donors>=1")
    outcome, _, predictors = MODELS["H1"]
    core = [outcome] + predictors
    columns = core + [k for k in AUX if k in data and data[k].notna().sum() >= 10]
    base = data[columns].reset_index(drop=True).copy()
    if any(base[k].notna().sum() < 10 for k in core):
        raise ValueError("Insufficient observed donors for a required H1 variable")
    rng = np.random.default_rng(seed)
    masks = {k: base[k].isna().to_numpy() for k in columns}
    for chain in range(m):
        work = base.copy()
        for key in columns:
            mask = masks[key]
            if mask.any():
                work.loc[mask,key] = rng.choice(base.loc[~mask,key].to_numpy(), size=mask.sum())
        for sweep in range(sweeps):
            for key in rng.permutation(columns):
                mask = masks[key]
                if not mask.any():
                    continue
                obs = np.flatnonzero(~mask)
                mis = np.flatnonzero(mask)
                x = matrix(work, [k for k in columns if k != key])
                values = base.loc[~mask,key].to_numpy()
                y = (np.column_stack([values == c for c in SOURCES]).astype(float)
                     if key == "source" else values.astype(float)[:,None])
                boot = rng.integers(0,len(obs),len(obs))
                coef = np.linalg.lstsq(x[obs[boot]], y[boot], rcond=1e-10)[0]
                scores = x @ coef
                # Stable nearest donor ordering, with random tie-breaks.
                for i in mis:
                    distance = ((scores[obs]-scores[i])**2).sum(axis=1)
                    nearest = np.lexsort((rng.random(len(obs)),distance))[:min(donors,len(obs))]
                    work.at[i,key] = values[rng.choice(nearest)]
            if trace is not None:
                trace(chain, sweep, work, masks)
        yield work, masks[outcome]


def pool(estimates):
    """Rubin pooling with Barnard–Rubin small-sample degrees of freedom."""
    m = len(estimates)
    if m < 2:
        raise ValueError("Rubin pooling requires at least two imputations")
    try:
        q = np.asarray([a["beta"] for a in estimates], dtype=float)
        se = np.asarray([a["se_hc3"] for a in estimates], dtype=float)
        sizes = np.asarray([a["n"] for a in estimates], dtype=float)
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Malformed complete-data inference") from exc
    if (q.shape != (m,) or se.shape != (m,) or sizes.shape != (m,)
            or not np.isfinite(q).all() or not np.isfinite(se).all()
            or not np.isfinite(sizes).all() or (se <= 0).any()
            or (sizes != np.floor(sizes)).any() or (sizes != sizes[0]).any()):
        raise ValueError("Invalid inference or inconsistent imputed sample sizes")
    # H1 includes the intercept and an extra dummy for the three-level source.
    dfcom = int(sizes[0]) - (len(MODELS["H1"][2]) + 2)
    if dfcom <= 0:
        raise ValueError("Nonpositive complete-data degrees of freedom")
    with np.errstate(over="ignore", invalid="ignore"):
        b = float(q.var(ddof=1))
        w = float(np.mean(se**2))
        total = w+(1+1/m)*b
    if not np.isfinite([b,w,total]).all() or w <= 0 or total <= 0:
        raise ValueError("Nonpositive or nonfinite pooled variance")
    fraction = (1+1/m)*b/total
    # w/total is algebraically 1-fraction but avoids cancellation near 1.
    dfobs = (dfcom+1)/(dfcom+3)*dfcom*(w/total)
    if not np.isfinite(dfobs) or dfobs <= 0:
        raise ValueError("Invalid observed-data degrees of freedom")
    df = dfobs if fraction == 0 else dfobs/(1+dfobs*fraction**2/(m-1))
    beta = float(q.mean())
    se = float(np.sqrt(total))
    critical = t.ppf(.975,df)
    lo, hi = float(beta-critical*se), float(beta+critical*se)
    p = float(2*t.sf(abs(beta/se),df))
    if not np.isfinite([beta,se,df,lo,hi,p]).all() or df <= 0 or not 0 <= p <= 1:
        raise ValueError("Nonfinite pooled inference")
    return dict(m=m,n=int(sizes[0]),beta=beta,se=se,df=float(df),
                ci95=[lo,hi],p=p,between_variance=b,within_variance=w,
                fraction_missing_information_approx=float(fraction))


def shift_outcome(completed, missing_outcome, delta, slope=0.0):
    """Pattern-mixture shift: delta + slope*(expression-5)/5, only missing outcomes."""
    shifted = completed.copy()
    adjustment = delta + slope*(shifted.loc[missing_outcome,"motive_expression"]-5)/5
    shifted.loc[missing_outcome,"clarity_post"] = (
        shifted.loc[missing_outcome,"clarity_post"]+adjustment).clip(0,10)
    return shifted


def sensitivity(raw,m=50,sweeps=15,seed=1729):
    data,_ = prepare(raw)
    # Slope denotes the additional shift at expression=10 relative to expression=5.
    # Shared imputations avoid Monte Carlo noise in comparisons across scenarios.
    grid = [(delta,0) for delta in DELTAS] + [
        (delta,slope) for delta in (-1,0,1) for slope in (-2,-1,1,2)]
    estimates = {key: [] for key in grid}
    for completed, missing_outcome in draw_imputations(data,m,sweeps,seed):
        for delta,slope in grid:
            shifted = shift_outcome(completed,missing_outcome,delta,slope)
            estimates[(delta,slope)].append(fit(shifted,"H1"))
    return {"eligible_n":len(data),"intake_flow":data.attrs["intake_flow"],"missing_clarity_n":int(data.clarity_post.isna().sum()),
            "seed":seed,"sweeps":sweeps,"method":"bootstrap chained donor matching",
            "scenarios":[{"delta":delta,**pool(estimates[(delta,0)])} for delta in DELTAS],
            "differential_scenarios":[{"delta":delta,"slope":slope,**pool(estimates[(delta,slope)])}
                                      for delta,slope in grid if slope != 0]}


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("csv",type=Path)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--data-kind",choices=["synthetic","empirical"],required=True)
    p.add_argument("--m",type=int,default=50)
    p.add_argument("--sweeps",type=int,default=15)
    p.add_argument("--seed",type=int,default=1729)
    a=p.parse_args()
    result=sensitivity(read_records(a.csv),a.m,a.sweeps,a.seed)
    result["data_kind"]=a.data_kind
    result["confirmatory_authorized"]=False
    result["calibration_status"]="development_sensitivity_only"
    a.out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
