"""Expanded two-group development calibration; no empirical group comparisons."""
import argparse,json
import numpy as np
from invariance_calibration import group
from invariance import compare_groups
from robust_calibration import wilson

def run(reps=20,seed=20261126,offset=0):
    if reps<1 or offset<0: raise ValueError("invalid replication range")
    d=np.repeat(np.arange(2),4); out=[]
    tests={"invariant":"threshold_loading_intercept","threshold_dif":"threshold_shape",
           "loading_dif":"threshold_loading","intercept_dif":"threshold_loading_intercept"}
    sizes=[(250,250),(350,150),(400,400),(560,240)]
    for sid,(n1,n2) in enumerate(sizes):
        for tid,(scenario,target) in enumerate(tests.items()):
            rows=[]
            for i in range(offset,offset+reps):
                rng=np.random.default_rng(np.random.SeedSequence([seed,sid,tid,i]))
                try:
                    f=compare_groups(group(n1,rng,scenario,False),group(n2,rng,scenario,True),d)
                    rows.append({"replicate":i,"status":"proper","target_rejected":f["tests"][target]["p_value"]<.05,
                                 "any_gate_rejected":f["ordered_gate"].endswith("_rejected"),**f})
                except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
                    rows.append({"replicate":i,"status":"failure","reason":str(exc)})
            proper=[x for x in rows if x["status"]=="proper"]
            reject=sum(x["target_rejected"] for x in proper)
            gate=sum(x["any_gate_rejected"] for x in proper)
            out.append({"sizes":[n1,n2],"scenario":scenario,"target":target,
                        "requested":reps,"proper":len(proper),"proper_interval":wilson(len(proper),reps),
                        "target_rate_unconditional":reject/reps,
                        "target_rate_conditional":reject/len(proper) if proper else None,
                        "target_interval_conditional":wilson(reject,len(proper)) if proper else None,
                        "any_gate_rejection_unconditional":gate/reps,"records":rows})
    return {"label":"SYNTHETIC DEVELOPMENT; eight items, not final invariance power","seed":seed,"offset":offset,"scenarios":out}
if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--reps",type=int,default=20)
    p.add_argument("--seed",type=int,default=20261126); p.add_argument("--offset",type=int,default=0)
    a=p.parse_args()
    print(json.dumps(run(a.reps,a.seed,a.offset),indent=2,allow_nan=False))
