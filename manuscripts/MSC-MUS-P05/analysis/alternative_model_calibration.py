"""Prospective independent EFA/CFA structural-discrimination screen."""
import argparse,json
import numpy as np
from alternative_structure import STRUCTURES,generate,factor_covariance
from model_comparison import reference,summary,MODELS
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
    # A higher-order model is nested within the correlated-seven covariance
    # family; correct recovery is not a forced unique winner by fit indices.
    diagnostics={}
    for m in MODELS:
        fits=[next(x for x in r["cfa"] if x["model"]==m) for r in rows]
        valid=[x for x in fits if x["status"]=="PROPER" and x.get("p_scaled") is not None]
        rejects=sum(x["p_scaled"]<.05 for x in valid)
        diagnostics[m]={"available":len(valid),"rejections":rejects,"operational_rate":rejects/reps,
                        "operational_interval":wilson(rejects,reps),
                        "conditional_rate":rejects/len(valid) if valid else None}
    selected={}
    for r in rows:
        key=str(r["efa"]["selected"])
        selected[key]=selected.get(key,0)+1
    return dict(n=n,structure=structure,generating_covariance=factor_covariance(structure).tolist(),
                loading=loading,skew=skew,item_mcar=missing,requested=reps,pa_reps=pa_reps,seed=seed,offset=offset,
                reference_summary=summary(rows),fit_rejection_diagnostics=diagnostics,
                efa_selected_counts=selected,efa_correct_count=sum(r["efa"]["correct_count"] for r in rows),
                efa_joint_recovery=sum(r["efa"]["joint_recovery"] for r in rows),records=rows,
                model_selection_authorized=False)

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
    a=p.parse_args()
    out=[cell(a.n,s,a.loading,a.skew,a.missing,a.reps,a.pa_reps,a.seed,a.offset) for s in ([a.structure] if a.structure else STRUCTURES)]
    print(json.dumps({"synthetic":True,"model_selection_authorized":False,"cells":out},indent=2,allow_nan=False))
