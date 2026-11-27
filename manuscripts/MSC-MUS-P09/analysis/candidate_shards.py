"""Deterministic, resumable calibration of the actual P09 IPW candidate.
Shard indices, not wall time, determine independent seeds. No participant data.
"""
import argparse
import itertools
import json
from pathlib import Path
import numpy as np
from calibration import generate,effect_values,PROFILES,MECHANISMS,STRESS_MECHANISMS,EFFECTS,STRESS_EFFECTS,validate_effect_profile
from inference import MODELS
from assignment_candidate import candidate_family
from calibrate_assignment_candidate import proportion

GRID=list(itertools.product((440,600),("complete","MCAR","MAR","MNAR"),
                            ("null","all_positive","distance_only"),("standard",)))
GRID+=list(itertools.product((440,600),("MAR_nonlinear","MAR_low_overlap"),
                             ("null","all_positive"),("standard","ceiling")))
VERSION="p09-candidate-shards-v1"

def resolve_design(cell,design=None):
    if not 0<=cell<len(GRID):raise ValueError("Invalid cell")
    if design is None:return GRID[cell]
    n,mechanism,effect,profile=design
    if type(n) is not int or n<40 or n>100000 or n%2 or mechanism not in MECHANISMS+STRESS_MECHANISMS or profile not in PROFILES:
        raise ValueError("Invalid custom design")
    validate_effect_profile(effect,profile)
    return n,mechanism,effect if isinstance(effect,str) else tuple(effect),profile

def parse_design(values):
    if values is None:return None
    n,mechanism,effect,profile=values
    return int(n),mechanism,tuple(map(float,effect.split(","))) if "," in effect else effect,profile

def replicate(seed,cell,index,draws,design=None):
    n,mechanism,effect,profile=resolve_design(cell,design)
    rng=np.random.default_rng(np.random.SeedSequence([seed,cell,index]))
    d=generate(rng,n,profile,mechanism,effect,allocation="stratified_blocks")
    d["target_status1"]=d["target_status2"]="defined"
    report=candidate_family(d,reps=draws,seed=int(rng.integers(0,2**32)))
    keys=("contrast","candidate_available","candidate_ci","candidate_p","unavailable","attempted","successful","failed")
    return {"index":index,"hypotheses":{h:{k:v for k,v in row.items() if k in keys}
              for h,row in report["hypotheses"].items()},"holm":report["candidate_secondary_holm"]}

def shard(seed,cell,start,count,draws,design=None):
    if not 0<=cell<len(GRID) or start<0 or count<1 or draws<199:
        raise ValueError("Invalid shard specification")
    resolve_design(cell,design)
    result={"schema":VERSION,"seed":seed,"cell":cell,"draws":draws,
            "records":[replicate(seed,cell,i,draws,design) if design is not None else replicate(seed,cell,i,draws) for i in range(start,start+count)]}
    if design is not None:result["design"]=list(design)
    return result

def aggregate(parts,expected):
    if not parts or expected<1:raise ValueError("No shards or invalid denominator")
    key=lambda p:(p["schema"],p["seed"],p["cell"],p["draws"],resolve_design(p["cell"],p["design"]) if "design" in p else None)
    meta=key(parts[0])
    if meta[0]!=VERSION or not 0<=meta[2]<len(GRID) or any(key(p)!=meta for p in parts):
        raise ValueError("Mixed shard metadata")
    rows=sorted((r for p in parts for r in p["records"]),key=lambda r:r["index"])
    if [r["index"] for r in rows]!=list(range(expected)):
        raise ValueError("Missing or duplicate replicate indices")
    n,mechanism,effect,profile=resolve_design(meta[2],meta[4])
    truth=dict(zip(MODELS,effect_values(effect)))
    models={}
    for h,t in truth.items():
        data=[r["hypotheses"][h] for r in rows]
        errors=np.asarray([r["contrast"]-t for r in data if "contrast" in r])
        valid=[r for r in data if r["candidate_available"]]
        covered=[r["candidate_ci"][0]<=t<=r["candidate_ci"][1] for r in valid]
        reject=[r["candidate_p"]<=.05 for r in valid]
        models[h]={"truth":t,"availability":proportion([r["candidate_available"] for r in data]),
                   "point_fits":len(errors),"bias":float(errors.mean()) if len(errors) else None,
                   "bias_mcse":float(errors.std(ddof=1)/np.sqrt(len(errors))) if len(errors)>1 else None,
                   "rmse":float(np.sqrt(np.mean(errors**2))) if len(errors) else None,
                   "conditional_coverage":proportion(covered),
                   "operational_coverage":proportion(covered+[False]*(expected-len(valid))),
                   "conditional_rejection":proportion(reject),
                   "operational_rejection":proportion(reject+[False]*(expected-len(valid))),
                   "unavailable_reasons":{reason:sum(r.get("unavailable")==reason for r in data)
                       for reason in sorted({r["unavailable"] for r in data if "unavailable" in r})},
                   "bootstrap_attempted":sum(r["attempted"] for r in data),
                   "bootstrap_successful":sum(r["successful"] for r in data),
                   "bootstrap_failed":sum(r["failed"] for r in data)}
        if h in ("H2","H3"):
            models[h]["holm_operational_rejection"]=proportion([r["holm"][h] is not None and r["holm"][h]<=.05 for r in rows])
    nulls=[h for h in ("H2","H3") if truth[h]==0]
    fwer=proportion([any(r["holm"][h] is not None and r["holm"][h]<=.05 for h in nulls) for r in rows]) if nulls else None
    return {"schema":VERSION,"seed":meta[1],"cell":meta[2],"draws":meta[3],"outer_reps":expected,
            "n":n,"mechanism":mechanism,"effect":effect,"profile":profile,
            "hypotheses":models,"secondary_true_null_fwer":fwer,
            "precision_screen_only":meta[4] is not None or expected<2000 or meta[3]<999,"confirmatory_authorized":False}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    s=sub.add_parser("shard")
    for arg in ("cell","start","count"):s.add_argument(arg,type=int)
    s.add_argument("--seed",type=int,default=20261206)
    s.add_argument("--draws",type=int,default=999)
    a=sub.add_parser("aggregate");a.add_argument("folder");a.add_argument("--expected",type=int,required=True)
    s.add_argument("--design",nargs=4)
    args=p.parse_args()
    if args.command=="shard":out=shard(args.seed,args.cell,args.start,args.count,args.draws,parse_design(args.design))
    else:out=aggregate([json.loads(f.read_text()) for f in sorted(Path(args.folder).glob("shard-*.json"))],args.expected)
    print(json.dumps(out,indent=2,allow_nan=False))
