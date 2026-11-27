"""Paired synthetic IPW/AIPW screening using the same datasets and bootstrap seeds."""
import argparse,json
import numpy as np
from calibration import generate,effect_values
from candidate_shards import GRID,VERSION
from assignment_candidate import candidate_family
from augmented_candidate import augmented_family
from calibrate_assignment_candidate import proportion
from inference import MODELS
from candidate_shards import aggregate

def run(cell,reps,draws,seed):
    if not 0<=cell<len(GRID) or reps<2 or draws<199:raise ValueError("Invalid screen")
    n,mechanism,effect,profile=GRID[cell]
    records={m:[] for m in ("ipw","aipw")}
    for i in range(reps):
        rng=np.random.default_rng(np.random.SeedSequence([seed,cell,i]))
        d=generate(rng,n,profile,mechanism,effect,allocation="stratified_blocks")
        d["target_status1"]=d["target_status2"]="defined"
        bootstrap_seed=int(rng.integers(0,2**32))
        for method,fn in (("ipw",candidate_family),("aipw",augmented_family)):
            report=fn(d,reps=draws,seed=bootstrap_seed)
            records[method].append(dict(index=i,hypotheses=report["hypotheses"],holm=report["candidate_secondary_holm"]))
    summaries={m:aggregate([dict(schema=VERSION,seed=seed,cell=cell,draws=draws,records=rows)],reps)
               for m,rows in records.items()}
    paired={}
    for h,t in zip(MODELS,effect_values(effect)):
        a,b=[[r["hypotheses"][h] for r in records[m]] for m in ("ipw","aipw")]
        pair=[(x,y) for x,y in zip(a,b) if "contrast" in x and "contrast" in y]
        diff=np.array([(y["contrast"]-t)**2-(x["contrast"]-t)**2 for x,y in pair])
        paired[h]={"both_points":len(pair),"both_available":sum(x["candidate_available"] and y["candidate_available"] for x,y in zip(a,b)),
                   "mean_squared_error_difference_aipw_minus_ipw":float(diff.mean()) if len(diff) else None,
                   "difference_mcse":float(diff.std(ddof=1)/np.sqrt(len(diff))) if len(diff)>1 else None}
    return {"synthetic":True,"paired":True,"seed":seed,"cell":cell,"methods":summaries,
            "paired_comparison":paired,"records":records,"confirmatory_authorized":False}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cell",type=int,default=19)
    p.add_argument("--reps",type=int,default=2)
    p.add_argument("--draws",type=int,default=199)
    p.add_argument("--seed",type=int,default=20261209)
    a=p.parse_args()
    print(json.dumps(run(a.cell,a.reps,a.draws,a.seed),indent=2,allow_nan=False))
