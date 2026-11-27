"""Calibrate production participant-bootstrap intervals against explicit population targets."""
import argparse
import json
import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.optimize import brentq
from simulation import draw
from inference import PREDICTORS,fit_arrays
from sensitivity import cluster_bootstrap

def complete_data(rng,n,m,beta):
    g,x,y=draw(rng,n,m,beta,missing=0)
    return g,x,np.clip(np.rint(y),0,10)

def dataset(rng,n,m,beta,missing,kind):
    g,x,y=complete_data(rng,n,m,beta)
    risk=.25*(x[:,1]-5)+.1*(x[:,0]-5)
    if kind=="mcar": risk=np.zeros(len(y))
    elif kind=="mnar": risk=risk+.45*(y-5)+.15*(x[:,0]-5)*(y-5)
    elif kind!="mar": raise ValueError("Unknown mechanism")
    z=brentq(lambda z:expit(z+risk).mean()-missing,-40,40)
    observed=rng.random(len(y))>=expit(z+risk)
    frame=pd.DataFrame(x,columns=PREDICTORS)
    frame["participant_id"]=g
    frame["interference"]=np.where(observed,y,np.nan)
    return frame

def run(reps=100,bootstrap=499,reference_n=100000,n=160,seed=2609):
    if min(reps,bootstrap)<1 or reference_n<100 or n<10:
        raise ValueError("Invalid replication or sample count")
    rng=np.random.default_rng(seed)
    cells=[]
    for beta in [0,.15]:
        reference=fit_arrays(*complete_data(rng,reference_n,6,beta))
        target=0. if beta==0 else reference["estimate"][0]
        for kind in ["mcar","mar","mnar"]:
            labels=[*(f"ipw/{cap}" for cap in (10,20)),
                    *(f"shift/{s:+d}/{a:+d}" for s in (-2,-1,0,1,2) for a in (-1,0,1))]
            methods={label:{"point":[],"width":[],"covered":[]} for label in labels}
            envelope=[]; valid_draws=[]; failed=0
            for _ in range(reps):
                frame=dataset(rng,n,6,beta,.30,kind)
                try:
                    out=cluster_bootstrap(frame,reps=bootstrap,seed=int(rng.integers(2**32)))
                except (ValueError,ArithmeticError,np.linalg.LinAlgError):
                    failed+=1
                    continue
                shift=out["point"]["pattern_mean_shifts"]
                envelope.append(min(shift.values())<=target<=max(shift.values()))
                valid_draws.append(out["valid"])
                for label,point,interval in [
                    *(("ipw/"+k,v,out["ipw_ci"][k]) for k,v in out["point"]["ipw"].items()),
                    *(("shift/"+k,v,out["shift_ci"][k]) for k,v in shift.items())]:
                    m=methods[label]
                    m["point"].append(point)
                    if interval is not None:
                        m["width"].append(interval[1]-interval[0])
                        m["covered"].append(interval[0]<=target<=interval[1])
            summary={}
            for label,m in methods.items():
                points=np.asarray(m["point"]); v=len(m["covered"]); k=sum(m["covered"])
                rate=k/v if v else None
                op=k/reps
                summary[label]={"point_valid":len(points),"interval_valid":v,
                    "interval_unavailable":reps-v,"bias":float(points.mean()-target) if len(points) else None,
                    "bias_mcse":float(points.std(ddof=1)/np.sqrt(len(points))) if len(points)>1 else None,
                    "coverage_conditional":rate,
                    "coverage_conditional_mcse":float(np.sqrt(rate*(1-rate)/v)) if v else None,
                    "coverage_operational":op,"coverage_operational_mcse":float(np.sqrt(op*(1-op)/reps)),
                    "mean_width":float(np.mean(m["width"])) if v else None}
            cells.append(dict(beta=beta,mechanism=kind,missing=.30,n=n,target=target,
                reference_se=reference["se"][0],requested=reps,point_failures=failed,methods=summary,
                mean_valid_bootstrap=float(np.mean(valid_draws)) if valid_draws else None,
                shift_envelope_fraction=float(np.mean(envelope)) if envelope else None,
                shift_envelope_available=len(envelope),
                shift_envelope_operational=sum(envelope)/reps,
                shift_envelope_is_ci=False))
    return dict(status="SYNTHETIC_BOOTSTRAP_V2",seed=seed,reps=reps,bootstrap=bootstrap,
                reference_n=reference_n,cells=cells,
                interpretation="Coverage against the complete-outcome reference, not a guarantee under MNAR or a validated shift estimand.",
                screening_only=bootstrap<499 or reps<1000)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name,value in [("reps",100),("bootstrap",499),("reference-n",100000),("n",160),("seed",2609)]:
        p.add_argument("--"+name,type=int,default=value)
    a=p.parse_args()
    print(json.dumps(run(a.reps,a.bootstrap,a.reference_n,a.n,a.seed),indent=2,allow_nan=False))
