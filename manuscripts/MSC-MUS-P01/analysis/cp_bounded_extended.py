"""Expanded synthetic CP sensitivity; preserves the original bounded grid."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from itertools import product
import json
import os
from pathlib import Path
import sys
import numpy as np
from scipy.special import expit
from scipy.stats import t
from cp_bounded import SCORES, probabilities, moments, infer

SIZES=(1600,2000,2400,3000,4000,5000)
EFFECTS=((0.,0.),(.15,.15),(.3,.3),(.45,.45),(.6,.6),
         (.15,.45),(.45,.15),(0.,.6),(.6,0.),(-.1,.7),(.7,-.1))
CENTRES=(.15,.5,.85)
MECHANISMS=("complete","mcar","mar","mnar","mnar_matched","mnar_mismatched")
CONCENTRATIONS=(8.,40.)
SHIFTS={"pm_common_minus1":(-1.,)*4,
        "pm_common_plus1":(1.,)*4,
        "pm_matched_minus1":(-1.,0.,0.,-1.),
        "pm_matched_plus1":(1.,0.,0.,1.),
        "pm_opposed":(-1.,1.,1.,-1.)}

def cell_probabilities(centre,effect,mechanism,concentration,cell):
    if mechanism not in ("mnar_matched","mnar_mismatched"):
        return probabilities(centre,effect,mechanism,concentration)
    pmf=probabilities(centre,effect,"complete",concentration).sum(-1)
    target=(cell in (0,3))==(mechanism=="mnar_matched")
    x=np.array([-1.,1.])[:,None]
    # Opposite outcome dependence, plus differential retention.
    # This can produce a spurious matching effect under the union null.
    sign=1 if target else -1
    ret=expit(1.9+.9*x+sign*(.45+.38*(SCORES[None,:]-5)))
    return np.stack((pmf*ret,pmf*(1-ret)),axis=-1)

def pattern_mixture(observed,total,truth,delta):
    """Fixed missing-minus-observed mean shifts; bounded at 0 and 10.

    Stratum weights are the known population probabilities .5/.5.
    Pointwise delta-method variance includes observed mean and retention
    uncertainty; this is a working approximation, not an MNAR correction.
    """
    n,m,v=moments(observed)
    frac=n/np.maximum(total,1)
    shifted=m+np.asarray(delta)[None,:,None]
    missing_mean=np.clip(shifted,0.,10.)
    adjusted=frac*m+(1-frac)*missing_mean
    derivative=frac+(1-frac)*((shifted>0)&(shifted<10))
    qmean=derivative**2*v/np.maximum(n,1)/4
    qret=(m-missing_mean)**2*frac*(1-frac)/np.maximum(total,1)/4
    q=(qmean+qret).sum(2)
    w=(qmean**2/np.maximum(n-1,1)+qret**2/np.maximum(total-1,1)).sum(2)
    mu=adjusted.mean(2)
    s=np.column_stack((mu[:,0]-mu[:,1],mu[:,3]-mu[:,2]))
    se2=np.column_stack((q[:,:2].sum(1),q[:,2:].sum(1)))
    denom=np.column_stack((w[:,:2].sum(1),w[:,2:].sum(1)))
    good=(n>=2).all((1,2))&(q>0).all(1)&(denom>0).all(1)
    with np.errstate(divide="ignore",invalid="ignore"):
        df=se2**2/denom
        p=t.sf(s/np.sqrt(se2),df)
        radius=t.ppf(.975,df)*np.sqrt(se2)
    good &= np.isfinite(p).all(1)&np.isfinite(radius).all(1)
    rejected=good&(p.max(1)<=.05)
    k=int(good.sum())
    errors=s[good]-truth
    rate=float(rejected.mean())
    return dict(valid=k,failed=len(good)-k,joint=rate,
                mcse=float(np.sqrt(rate*(1-rate)/len(good))),
                bias=errors.mean(0).tolist() if k else None,
                rmse=np.sqrt((errors**2).mean(0)).tolist() if k else None,
                coverage=(np.abs(errors)<=radius[good]).mean(0).tolist() if k else None)

def simulate_cell(task):
    index,scenario,reps,seed=task
    n,e,centre,mechanism,concentration=scenario
    rng=np.random.default_rng(np.random.SeedSequence([seed,index]))
    effects=(e[0],0.,0.,e[1])
    counts=np.stack([rng.multinomial(n//4,cell_probabilities(centre,delta,mechanism,concentration,i).ravel(),size=reps).reshape(reps,2,11,2) for i,delta in enumerate(effects)],axis=1)
    observed=counts[...,0]
    total=counts.sum((3,4))
    methods={m:infer(observed,m,np.asarray(e)) for m in ("available","standardised")}
    for name,delta in SHIFTS.items():
        methods[name]=pattern_mixture(observed,total,np.asarray(e),delta)
    return dict(n=n,e=list(e),centre=centre,mechanism=mechanism,concentration=concentration,
                requested=reps,union_null=min(e)<=0,
                mean_retention=float(observed.sum((1,2,3)).mean()/n),
                retention_by_cell=(observed.sum((2,3)).mean(0)/(n//4)).tolist(),
                methods=methods)

def design(smoke=False):
    if smoke:
        return list(product((1600,),((0.,.6),(.3,.3)),(.5,),MECHANISMS,(8.,)))
    return list(product(SIZES,EFFECTS,CENTRES,MECHANISMS,CONCENTRATIONS))

def atomic_write(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(payload,indent=2,allow_nan=False),encoding="utf-8")
    tmp.replace(path)

def run(reps=2000,seed=20261129,workers=1,smoke=False,output=None):
    if reps<1 or seed<0 or workers<1:
        raise ValueError("Positive reps/workers and non-negative seed required")
    grid=design(smoke)
    tasks=[(i,s,reps,seed) for i,s in enumerate(grid)]
    payload=dict(status="SYNTHETIC_DEVELOPMENT",version="1.0.0",seed=seed,reps=reps,
                 planned_cells=len(grid),complete=False,confirmatory_authorized=False,
                 numpy_version=np.__version__,pattern_mixture_shifts=SHIFTS,cells=[])
    if output is not None:
        output=Path(output)
        if output.exists():
            raise FileExistsError("Choose a new output file; existing results are preserved")
    def record(iterator):
        for i,cell in enumerate(iterator,1):
            payload["cells"].append(cell)
            if i==1 or i%10==0 or i==len(grid):
                print(f"{i}/{len(grid)} scenarios completed",file=sys.stderr,flush=True)
                if output is not None:
                    atomic_write(output,payload)
    if workers==1:
        record(map(simulate_cell,tasks))
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            record(pool.map(simulate_cell,tasks,chunksize=1))
    payload["complete"]=True
    if output is not None:
        atomic_write(output,payload)
    return payload

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reps",type=int,default=2000)
    p.add_argument("--seed",type=int,default=20261129)
    p.add_argument("--workers",type=int,default=min(8,os.cpu_count() or 1))
    p.add_argument("--smoke",action="store_true")
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    run(a.reps,a.seed,a.workers,a.smoke,a.output)
