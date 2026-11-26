"""Extended synthetic calibration; no clinical or participant observations."""
import argparse
import json
import numpy as np
from inference import (impute_pmm,pooled_contrast,target_weights,shift_imputed)
from simulation import generate,wilson

def robustness(x,y,draws,w,mar):
    # Reuse the same draws across all 27 sensitivity scenarios.
    lower,upper=mar["lower"],mar["upper"]
    # To certify a directional result every interval must exclude zero.
    positive=lower>0
    negative=upper<0
    if not (positive or negative):
        return False
    for i in (-2,0,2):
        for j in (-2,0,2):
            for s in (-1,0,1):
                q=pooled_contrast(x,shift_imputed(x,y,draws,i,j,s),w)
                if (positive and q["lower"]<=0) or (negative and q["upper"]>=0):
                    return False
    return True

def run_scenario(n,delta,mechanism,reps,m,seed):
    rng=np.random.default_rng(seed)
    rows=[]
    failed=0
    for _ in range(reps):
        try:
            x,y,truth=generate(n,delta,mechanism,rng)
            w=target_weights(x)
            draws=impute_pmm(x,y,m,int(rng.integers(2**32-1)))
            q=pooled_contrast(x,draws,w)
            robust=robustness(x,y,draws,w,q)
            rows.append((q["estimate"]-truth,q["p"]<.05,
                         q["lower"]<=truth<=q["upper"],robust,np.isnan(y).mean()))
        except (ValueError,np.linalg.LinAlgError):
            failed+=1
    if not rows:
        raise RuntimeError("No valid calibration replications")
    a=np.asarray(rows)
    valid=len(a)
    out={"n_randomised":n,"true_composite_interaction":truth,"mechanism":mechanism,
         "requested":reps,"valid":valid,"failed":failed,"imputations":m,
         "bias":float(a[:,0].mean()),"bias_mcse":float(a[:,0].std(ddof=1)/np.sqrt(valid)),
         "mean_missing":float(a[:,4].mean())}
    for name,i in (("nominal_rejection",1),("coverage",2),("grid_robust_rejection",3)):
        k=int(a[:,i].sum())
        out[name]=k/valid
        out[name+"_mc95"]=wilson(k,valid)
    return out

def report(reps=120,m=10,seed=20261127):
    # Raw composite interactions .36, .54, .72; zero under MNAR assesses false positives.
    cases=[(n,d,"mar") for n in (640,1000,1600) for d in (.4,.6,.8)]
    cases += [(1000,0.,"mnar"),(1000,.6,"mnar")]
    return {"status":"SYNTHETIC_DESIGN_ONLY","seed":seed,
            "scenarios":[run_scenario(n,d,mech,reps,m,seed+i)
                         for i,(n,d,mech) in enumerate(cases)]}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--reps",type=int,default=120)
    p.add_argument("--imputations",type=int,default=10)
    a=p.parse_args()
    if min(a.reps,a.imputations)<2:
        p.error("At least two replications and imputations required")
    print(json.dumps(report(a.reps,a.imputations),indent=2,allow_nan=False))
