"""Targeted screening at the rounded ARC Music candidate sample sizes.

Synthetic data only. Uses existing production sensitivity/PMM routines.
Each command runs in a separate process to avoid same-name module collisions.
"""
import argparse
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
from scipy.stats import norm, rankdata

ROOT = Path(__file__).resolve().parent
SEED = 20261202


def load_path(study):
    sys.path.insert(0, str(ROOT / "manuscripts" / ("MSC-MUS-" + study) / "analysis"))


def wilson(hits, n):
    if n == 0:
        return None
    p = hits / n
    z = norm.ppf(.975)
    den = 1 + z*z/n
    mid = (p+z*z/(2*n))/den
    half = z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [float(max(0,mid-half)), float(min(1,mid+half))]


def coverage(intervals, attempted, truth=0.):
    valid = len(intervals)
    if not valid:
        return dict(attempted=attempted, valid=0, failures=attempted,
                    coverage=None, operational_coverage=0., coverage_ci95=None,
                    mean_width=None)
    intervals = np.asarray(intervals, float)
    if intervals.shape != (valid, 2) or not np.isfinite(intervals).all() or (intervals[:,1]<intervals[:,0]).any():
        raise ValueError("Invalid bootstrap interval")
    hits = int(((intervals[:,0]<=truth)&(truth<=intervals[:,1])).sum())
    return dict(attempted=attempted, valid=valid, failures=attempted-valid,
                coverage=hits/valid, operational_coverage=hits/attempted,
                coverage_ci95=wilson(hits,valid),
                mean_width=float(np.diff(intervals, axis=1).mean()))


def p08(n, mechanism, reps, draws, seed):
    import pandas as pd
    from inference import BASE
    from sensitivity import assess, bootstrap
    from simulation import draw
    if n not in (640,660) or mechanism not in ("mar","mnar"):
        raise ValueError("Invalid P08 design")
    intervals = {"ipw20": [], "shift_zero": []}
    heard_counts, gate_counts = [], []
    rng = np.random.default_rng(seed)
    for _ in range(reps):
        x,y,observed = draw(rng,n,0.,0.,mechanism,loss=.20,nonadherence=.15)
        # Depends on execution only: at the authority null, hearing does not
        # select on authority or the outcome. This is not a full-cohort effect.
        heard = rng.random(n) >= np.where(x[:,2] > 0,.10,.05)
        frame = pd.DataFrame(x[:,4:],columns=BASE)
        frame["authority"] = x[:,1]+.5
        frame["manual"] = x[:,2]+.5
        frame["heard_version"] = heard
        frame["ownership"] = np.where(heard & observed[0],y[0],np.nan)
        gate = assess(frame,"ownership")
        if gate["full_cohort_target_defined"] != bool(heard.all()):
            raise AssertionError("Full-cohort outcome gate failed")
        if not heard.all() and ("ipw" in gate or "shift_scenarios" in gate):
            raise AssertionError("Undefined outcomes must not receive full-cohort estimates")
        gate_counts.append(not gate["full_cohort_target_defined"])
        heard_counts.append([heard.sum(),(heard & observed[0]).sum()])
        result = bootstrap(frame,"ownership",draws,int(rng.integers(0,2**32)))
        if "unavailable" not in result:
            if result["valid"]+result["failures"] != draws:
                raise AssertionError("Inner accounting mismatch")
            intervals["ipw20"].append(result["ipw"]["20"]["authority"])
            intervals["shift_zero"].append(result["shift"]["0/0/0"]["authority"])
    return dict(n=n,mechanism=mechanism,reps=reps,draws=draws,
                truth=0.,target="descriptive authority null among known heard records",
                mean_heard=float(np.mean(heard_counts,axis=0)[0]),
                mean_observed_heard=float(np.mean(heard_counts,axis=0)[1]),
                full_cohort_gate_blocked=int(sum(gate_counts)),
                methods={k:coverage(v,reps) for k,v in intervals.items()})


def p09(n, mechanism, effect, reps, draws, seed):
    from calibration_extended import bootstrap_cell, raw_cell
    if n not in (440,600) or mechanism not in ("MAR","MNAR"):
        raise ValueError("Invalid P09 design")
    return dict(
        bootstrap=bootstrap_cell(seed,"H1",mechanism,effect,n,reps,draws,
                                 profile="heteroskedastic",allocation="stratified_blocks"),
        raw=raw_cell(seed+1,n,effect,"selective",reps),
        note="Raw-record diagnostic uses its own DGP; not the bootstrap population.")


def split_rhat(chains):
    """Rank-normalized and folded split Rhat, descriptive for PMM trace summaries."""
    values = np.asarray(chains,float)
    if values.ndim!=2 or values.shape[0]<2 or values.shape[1]<8 or not np.isfinite(values).all():
        raise ValueError("Invalid chains")
    half = values.shape[1]//2
    split = np.concatenate((values[:,:half],values[:,-half:]),axis=0)
    def statistic(a):
        if np.ptp(a)==0:
            return None
        ranks = rankdata(a.ravel()).reshape(a.shape)
        z = norm.ppf((ranks-.375)/(ranks.size+.25))
        w = z.var(axis=1,ddof=1).mean()
        if w<=0:
            return None
        b = half*z.mean(axis=1).var(ddof=1)
        return float(np.sqrt(((half-1)*w/half+b/half)/w))
    rank = statistic(split)
    folded = statistic(np.abs(split-np.median(split)))
    result = max(rank,folded) if rank is not None and folded is not None else None
    return dict(rank=rank,folded=folded,maximum=result)


def p03(mechanism, reps, seed):
    from imputation import draw_imputations
    from imputation_calibration import mask_and_stop,raw_records
    from power import calibration
    from stress import generate
    if mechanism not in ("mixed_mar","outcome_mnar"):
        raise ValueError("Invalid P03 mechanism")
    keys = ("clarity_post","motive_expression")
    chains,sweeps = 4,30
    rng = np.random.default_rng(seed)
    results = []
    for _ in range(reps):
        x,y = generate(rng,660,.6,calibration(.6,.15),True)
        data,n = mask_and_stop(rng,raw_records(x,y),mechanism,500)
        traces = {key:np.full((chains,sweeps,2),np.nan)
                  for key in keys if data[key].isna().any()}
        def record(chain,sweep,work,masks):
            for key,trace in traces.items():
                values = work.loc[masks[key],key].to_numpy(float)
                trace[chain,sweep] = [values.mean(),values.std(ddof=0)]
        for _ in draw_imputations(data,m=chains,sweeps=sweeps,
                                  seed=int(rng.integers(0,2**32)),trace=record):
            pass
        rows = {}
        for key,trace in traces.items():
            if not np.isfinite(trace).all():
                raise AssertionError("Incomplete trace")
            rows[key] = {label:split_rhat(trace[:,10:,i]) for i,label in enumerate(("mean","sd"))}
        results.append(dict(submitted=len(data),complete=n,diagnostics=rows))
    return dict(mechanism=mechanism,target=500,cap=660,reps=reps,chains=chains,
                sweeps=sweeps,discarded=10,rows=results,
                note="Summary-statistic diagnostics; not proof of convergence or MI validity.")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study",choices=("P03","P08","P09"),required=True)
    p.add_argument("--n",type=int,default=660)
    p.add_argument("--mechanism",required=True)
    p.add_argument("--effect",choices=("null","alternative"),default="null")
    p.add_argument("--reps",type=int,default=40)
    p.add_argument("--draws",type=int,default=199)
    p.add_argument("--seed",type=int,default=SEED)
    a=p.parse_args()
    if a.reps<2 or a.draws<199:
        p.error("Require >=2 outer replications and >=199 bootstrap draws")
    load_path(a.study)
    if a.study=="P03":
        results=p03(a.mechanism,a.reps,a.seed)
    elif a.study=="P08":
        results=p08(a.n,a.mechanism,a.reps,a.draws,a.seed)
    else:
        results=p09(a.n,a.mechanism,a.effect,a.reps,a.draws,a.seed)
    print(json.dumps(dict(synthetic=True,screening_only=True,study=a.study,
                          seed=a.seed,results=results),indent=2,allow_nan=False))


if __name__=="__main__":
    main()
