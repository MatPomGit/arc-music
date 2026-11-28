"""Prospective independent EFA/CFA structural-discrimination screen."""
import argparse,json
from pathlib import Path
import numpy as np
from alternative_structure import STRUCTURES,generate,factor_covariance
from model_comparison import reference,summary,MODELS,METHOD
from factor_count_calibration import assess
from robust_calibration import wilson

def cell(n,structure,loading,skew,missing,reps,pa_reps,seed,offset=0):
    if reps<1 or offset<0 or pa_reps<10:raise ValueError("Invalid design")
    k=1 if structure=="one_factor" else 7
    rows=[]
    for i in range(offset,offset+reps):
        es,cs,ps=np.random.SeedSequence([seed,STRUCTURES.index(structure),i]).spawn(3)
        efa=generate(n,structure,np.random.default_rng(es),loading,skew,missing)
        cfa=generate(n,structure,np.random.default_rng(cs),loading,skew,missing)
        rows.append({"replicate":i,"efa":assess(efa,k,35//k,loading,pa_reps,int(ps.generate_state(1)[0])),
                     "cfa":reference(cfa)})
    return summarize_cell(n,structure,loading,skew,missing,pa_reps,seed,offset,rows)

def summarize_cell(n,structure,loading,skew,missing,pa_reps,seed,offset,rows):
    reps=len(rows)
    if reps<1 or [r["replicate"] for r in rows]!=list(range(offset,offset+reps)):
        raise ValueError("Invalid structure replicate indices")
    # A higher-order model is nested within the correlated-seven covariance
    # family; correct recovery is not a forced unique winner by fit indices.
    diagnostics={}
    for m in MODELS:
        fits=[next(x for x in r["cfa"] if x["model"]==m) for r in rows]
        valid=[x for x in fits if x["status"]=="PROPER" and x.get("p_development") is not None]
        rejects=sum(x["p_development"]<.05 for x in valid)
        diagnostics[m]={"available":len(valid),"rejections":rejects,"operational_rate":rejects/reps,
                        "operational_interval":wilson(rejects,reps),
                        "conditional_rate":rejects/len(valid) if valid else None}
    selected={}
    for r in rows:
        key=str(r["efa"]["selected"])
        selected[key]=selected.get(key,0)+1
    return dict(method=METHOD,independent_reference_verified=False,n=n,structure=structure,generating_covariance=factor_covariance(structure).tolist(),
                loading=loading,skew=skew,item_mcar=missing,requested=reps,pa_reps=pa_reps,seed=seed,offset=offset,
                reference_summary=summary(rows),fit_rejection_diagnostics=diagnostics,
                efa_selected_counts=selected,efa_correct_count=sum(r["efa"]["correct_count"] for r in rows),
                efa_joint_recovery=sum(r["efa"]["joint_recovery"] for r in rows),records=rows,
                model_selection_authorized=False)

def aggregate(parts,expected):
    if not parts or expected<1:raise ValueError("Empty structural aggregate")
    names=("n","structure","loading","skew","item_mcar","pa_reps","seed")
    key=lambda p:tuple(p[k] for k in names)
    meta=key(parts[0])
    if any(key(p)!=meta or p.get("method")!=METHOD for p in parts):raise ValueError("Mixed structural metadata")
    for p in parts:
        if [r["replicate"] for r in p["records"]]!=list(range(p["offset"],p["offset"]+p["requested"])):
            raise ValueError("Invalid structural shard accounting")
    rows=sorted((r for p in parts for r in p["records"]),key=lambda r:r["replicate"])
    if [r["replicate"] for r in rows]!=list(range(expected)):
        raise ValueError("Missing or duplicate structural indices")
    return summarize_cell(*meta,0,rows)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--structure",choices=STRUCTURES)
    p.add_argument("--n",type=int,default=500)
    p.add_argument("--reps",type=int,default=1)
    p.add_argument("--pa-reps",type=int,default=10)
    p.add_argument("--seed",type=int,default=20261208)
    p.add_argument("--offset",type=int,default=0)
    p.add_argument("--loading",type=float,default=.65)
    p.add_argument("--skew",action="store_true")
    p.add_argument("--missing",type=float,default=0.)
    p.add_argument("--aggregate",type=Path)
    p.add_argument("--expected",type=int)
    a=p.parse_args()
    if a.aggregate:
        if a.expected is None:p.error("--aggregate requires --expected")
        parts=[json.loads(f.read_text()) for f in sorted(a.aggregate.glob("shard-*.json"))]
        if any(len(part["cells"])!=1 for part in parts):p.error("Each shard must contain one structure")
        out=[aggregate([part["cells"][0] for part in parts],a.expected)]
    else:
        if a.expected is not None:p.error("--expected requires --aggregate")
        out=[cell(a.n,s,a.loading,a.skew,a.missing,a.reps,a.pa_reps,a.seed,a.offset) for s in ([a.structure] if a.structure else STRUCTURES)]
    print(json.dumps({"synthetic":True,"model_selection_authorized":False,"cells":out},indent=2,allow_nan=False))
