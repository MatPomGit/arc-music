"""H1 multiple imputation and delta sensitivity via bootstrap donor matching."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import t
from models import prepare, fit, MODELS, SOURCES, RANGES

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


def draw_imputations(data, m=50, sweeps=15, seed=1729, donors=5):
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
    for _ in range(m):
        work = base.copy()
        for key in columns:
            mask = masks[key]
            if mask.any():
                work.loc[mask,key] = rng.choice(base.loc[~mask,key].to_numpy(), size=mask.sum())
        for _ in range(sweeps):
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
        yield work, masks[outcome]


def pool(estimates):
    """Rubin pooling with Barnard–Rubin small-sample degrees of freedom."""
    q = np.array([a["beta"] for a in estimates])
    u = np.array([a["se_hc3"]**2 for a in estimates])
    m = len(q)
    b = float(q.var(ddof=1))
    w = float(u.mean())
    total = w+(1+1/m)*b
    if not np.isfinite(total) or total <= 0:
        raise ValueError("Nonpositive or nonfinite pooled variance")
    dfcom = min(a["n"] for a in estimates)-12
    if dfcom <= 0:
        raise ValueError("Nonpositive complete-data degrees of freedom")
    fraction = (1+1/m)*b/total
    dfobs = (dfcom+1)/(dfcom+3)*dfcom*(1-fraction)
    df = dfobs if fraction == 0 else 1/(fraction**2/(m-1)+1/dfobs)
    beta = float(q.mean())
    se = float(np.sqrt(total))
    critical = t.ppf(.975,df)
    return dict(m=m,n=min(a["n"] for a in estimates),beta=beta,se=se,df=float(df),
                ci95=[float(beta-critical*se),float(beta+critical*se)],
                p=float(2*t.sf(abs(beta/se),df)),between_variance=b,within_variance=w,
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
    return {"eligible_n":len(data),"missing_clarity_n":int(data.clarity_post.isna().sum()),
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
    result=sensitivity(pd.read_csv(a.csv),a.m,a.sweeps,a.seed)
    result["data_kind"]=a.data_kind
    a.out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
