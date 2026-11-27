"""Paired synthetic IPW/AIPW screening using the same datasets and bootstrap seeds."""
import argparse,json
from pathlib import Path
import numpy as np
from calibration import generate,effect_values
from candidate_shards import GRID,VERSION,resolve_design,parse_design
from assignment_candidate import candidate_family
from augmented_candidate import augmented_family
from calibrate_assignment_candidate import proportion
from inference import MODELS
from candidate_shards import aggregate

SCHEMA="p09-paired-shard-v1"

def shard(cell,offset,reps,draws,seed,design=None):
    if not 0<=cell<len(GRID) or offset<0 or reps<1 or draws<199:raise ValueError("Invalid screen")
    n,mechanism,effect,profile=resolve_design(cell,design)
    records={m:[] for m in ("ipw","aipw")}
    for i in range(offset,offset+reps):
        rng=np.random.default_rng(np.random.SeedSequence([seed,cell,i]))
        d=generate(rng,n,profile,mechanism,effect,allocation="stratified_blocks")
        d["target_status1"]=d["target_status2"]="defined"
        bootstrap_seed=int(rng.integers(0,2**32))
        for method,fn in (("ipw",candidate_family),("aipw",augmented_family)):
            report=fn(d,reps=draws,seed=bootstrap_seed)
            records[method].append(dict(index=i,hypotheses=report["hypotheses"],holm=report["candidate_secondary_holm"]))
    result={"schema":SCHEMA,"seed":seed,"cell":cell,"draws":draws,"offset":offset,
            "requested":reps,"records":records}
    if design is not None:result["design"]=list(design)
    return result

def summarize(parts,reps):
    if not parts or reps<1:raise ValueError("Empty aggregate")
    key=lambda p:(p.get("schema"),p["seed"],p["cell"],p["draws"],resolve_design(p["cell"],p["design"]) if "design" in p else None)
    meta=key(parts[0])
    if meta[0]!=SCHEMA or not 0<=meta[2]<len(GRID) or any(key(p)!=meta for p in parts):
        raise ValueError("Mixed paired shard metadata")
    _,seed,cell,draws,design=meta
    effect=resolve_design(cell,design)[2]
    records={m:[] for m in ("ipw","aipw")}
    for p in parts:
        if set(p["records"])!=set(records):raise ValueError("Missing paired method")
        for m in records:
            rows=p["records"][m]
            if [r["index"] for r in rows]!=list(range(p["offset"],p["offset"]+p["requested"])):
                raise ValueError("Invalid paired shard indices")
            records[m].extend(rows)
    for m in records:
        records[m].sort(key=lambda row:row["index"])
        if [r["index"] for r in records[m]]!=list(range(reps)):
            raise ValueError("Missing or duplicate paired indices")
    summaries={m:aggregate([dict(schema=VERSION,seed=seed,cell=cell,draws=draws,records=rows,**({"design":list(design)} if design is not None else {}))],reps)
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

def run(cell,reps,draws,seed,design=None):
    return summarize([shard(cell,0,reps,draws,seed,design)],reps)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cell",type=int,default=19)
    p.add_argument("--reps",type=int,default=2)
    p.add_argument("--draws",type=int,default=199)
    p.add_argument("--seed",type=int,default=20261209)
    p.add_argument("--offset",type=int)
    p.add_argument("--aggregate",type=Path)
    p.add_argument("--expected",type=int)
    p.add_argument("--design",nargs=4)
    a=p.parse_args()
    if a.aggregate:
        if a.expected is None or a.offset is not None or a.design is not None:p.error("Aggregation requires --expected without --offset")
        result=summarize([json.loads(f.read_text()) for f in sorted(a.aggregate.glob("shard-*.json"))],a.expected)
    elif a.expected is not None:p.error("--expected requires --aggregate")
    elif a.offset is not None:result=shard(a.cell,a.offset,a.reps,a.draws,a.seed,parse_design(a.design))
    else:result=run(a.cell,a.reps,a.draws,a.seed,parse_design(a.design))
    print(json.dumps(result,indent=2,allow_nan=False))
