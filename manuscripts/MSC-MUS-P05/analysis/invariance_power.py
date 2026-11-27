"""Expanded two-group development calibration; no empirical group comparisons."""
import argparse,json
import numpy as np
from invariance_calibration import group
from invariance import compare_groups
from robust_calibration import wilson

REJECTED_GATES = frozenset({
    "configural_rejected", "threshold_shape_rejected",
    "threshold_loading_rejected", "threshold_loading_intercept_rejected",
})
NONREJECTED_GATE = "all_restrictions_not_rejected"


def gate_rejected(status):
    """Classify a completed ordered decision, never an intermediate status."""
    if status in REJECTED_GATES:
        return True
    if status == NONREJECTED_GATE:
        return False
    raise ValueError(f"unknown final ordered gate: {status!r}")


def summarize_gates(rows):
    """Keep failures in the requested denominator, not in the proper one."""
    proper = [row for row in rows if row["status"] == "proper"]
    failures = [row for row in rows if row["status"] == "failure"]
    if not rows or len(proper) + len(failures) != len(rows):
        raise ValueError("invalid replication accounting")
    rejected = sum(gate_rejected(row["ordered_gate"]) for row in proper)
    n = len(rows)
    m = len(proper)
    return {
        "failed": len(failures),
        "any_gate_rejected_count": rejected,
        "any_gate_not_rejected_count": m - rejected,
        "any_gate_rejection_unconditional": rejected / n,
        "any_gate_rejection_conditional": rejected / m if m else None,
        "any_gate_interval_unconditional": wilson(rejected, n),
        "any_gate_interval_conditional": wilson(rejected, m) if m else None,
    }


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
                except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
                    rows.append({"replicate":i,"status":"failure","reason":str(exc)})
                else:
                    rows.append({"replicate":i,"status":"proper","target_rejected":f["tests"][target]["p_value"]<.05,
                                 "any_gate_rejected":gate_rejected(f["ordered_gate"]),**f})
            proper=[x for x in rows if x["status"]=="proper"]
            reject=sum(x["target_rejected"] for x in proper)
            out.append({"sizes":[n1,n2],"scenario":scenario,"target":target,
                        "requested":reps,"proper":len(proper),"proper_interval":wilson(len(proper),reps),
                        "target_rate_unconditional":reject/reps,
                        "target_rate_conditional":reject/len(proper) if proper else None,
                        "target_interval_conditional":wilson(reject,len(proper)) if proper else None,
                        **summarize_gates(rows),"records":rows})
    return {"label":"SYNTHETIC DEVELOPMENT; eight items, not final invariance power","seed":seed,"offset":offset,"scenarios":out}
if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--reps",type=int,default=20)
    p.add_argument("--seed",type=int,default=20261126); p.add_argument("--offset",type=int,default=0)
    a=p.parse_args()
    print(json.dumps(run(a.reps,a.seed,a.offset),indent=2,allow_nan=False))
