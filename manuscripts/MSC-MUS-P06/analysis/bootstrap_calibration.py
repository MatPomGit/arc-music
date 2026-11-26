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
            points=[]; widths=[]; covered=[]; envelope=[]; valid_draws=[]; failed=0
            for _ in range(reps):
                frame=dataset(rng,n,6,beta,.30,kind)
                try:
                    out=cluster_bootstrap(frame,reps=bootstrap,seed=int(rng.integers(2**32)))
                    ci=out["ipw_ci"]["10"]
                    if ci is None or out["valid"]<.9*bootstrap:
                        failed+=1
                        continue
                    points.append(out["point"]["ipw"]["10"])
                    widths.append(ci[1]-ci[0])
                    covered.append(ci[0]<=target<=ci[1])
                    shift=out["point"]["pattern_mean_shifts"]
                    envelope.append(min(shift.values())<=target<=max(shift.values()))
                    valid_draws.append(out["valid"])
                except (ValueError,np.linalg.LinAlgError):
                    failed+=1
            v=len(points)
            cov=float(np.mean(covered)) if v else None
            cells.append(dict(beta=beta,mechanism=kind,missing=.30,n=n,target=target,
                reference_se=reference["se"][0],valid=v,failures=failed,
                bias=float(np.mean(points)-target) if v else None,
                ipw_ci_coverage=cov,coverage_mcse=float(np.sqrt(cov*(1-cov)/v)) if v else None,
                mean_width=float(np.mean(widths)) if v else None,
                mean_valid_bootstrap=float(np.mean(valid_draws)) if v else None,
                shift_envelope_fraction=float(np.mean(envelope)) if v else None))
    return dict(status="SYNTHETIC_BOOTSTRAP",seed=seed,reps=reps,bootstrap=bootstrap,
                reference_n=reference_n,cells=cells,
                screening_only=bootstrap<499 or reps<1000)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name,value in [("reps",100),("bootstrap",499),("reference-n",100000),("n",160),("seed",2609)]:
        p.add_argument("--"+name,type=int,default=value)
    a=p.parse_args()
    print(json.dumps(run(a.reps,a.bootstrap,a.reference_n,a.n,a.seed),indent=2,allow_nan=False))
