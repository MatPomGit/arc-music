"""Paired eight-item WLSMV and Python ordinal diagnostics on identical synthetic inputs."""
import argparse,json
from pathlib import Path
import numpy as np
from invariance_calibration import group
from invariance import compare_groups
from invariance_family import NAMES,global_decision
from invariance_family_calibration import rate

SCENARIOS=("invariant","threshold_dif","loading_dif","intercept_dif")
SIZES=((250,250),(350,150),(400,400),(560,240))
# Cumulative hypotheses: the generating DIF changes specific restrictions.
TRUE_NULLS={
    "invariant":NAMES,
    "threshold_dif":NAMES[:2],
    "loading_dif":NAMES[:3],
    "intercept_dif":NAMES[:4],
}
TARGET={"threshold_dif":"threshold_shape","loading_dif":"threshold_loading",
        "intercept_dif":"threshold_loading_intercept"}

def reference(x1,x2):
    # Preserve the unavailable denominator, never copy the local estimate.
    return {"status": "UNAVAILABLE", "reason": "Independent Python ordinal reference not established"}

def python_reference(x1,x2):
    try:
        f=compare_groups(x1,x2,np.repeat(np.arange(2),4))
        return {"status":"PROPER","decision":f["global_family_candidate"],
                "configural_p_values":f["configural_p_values"],"tests":f["tests"]}
    except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
        return {"status":"UNAVAILABLE","reason":str(exc)}

def summarize(rows,scenario,method):
    n=len(rows)
    if n<1:raise ValueError("No replicates")
    if any(r[method]["status"] not in ("PROPER","UNAVAILABLE","ERROR") for r in rows):
        raise ValueError("Invalid method status")
    proper=[r[method]["decision"] for r in rows if r[method]["status"]=="PROPER"]
    false=sum(bool(set(d["rejected_tests"])&set(TRUE_NULLS[scenario])) for d in proper)
    target=TARGET.get(scenario)
    detected=sum(target in d["rejected_tests"] for d in proper) if target else None
    return {"requested":n,"available":rate(len(proper),n),
            "true_null_fwer_operational":rate(false,n),
            "true_null_fwer_conditional":rate(false,len(proper)),
            "any_rejection_operational":rate(sum(d["any_rejected"] for d in proper),n),
            "target_rejection_operational":rate(detected,n) if target else None,
            "target_rejection_conditional":rate(detected,len(proper)) if target else None,
            "status_counts":{s:sum(r[method]["status"]==s for r in rows) for s in ("PROPER","UNAVAILABLE","ERROR")}}

def cell(sid,scenario,reps,seed,offset=0):
    if not 0<=sid<len(SIZES) or scenario not in SCENARIOS or reps<1 or offset<0:raise ValueError("Invalid design")
    n1,n2=SIZES[sid];tid=SCENARIOS.index(scenario);rows=[]
    for i in range(offset,offset+reps):
        rng=np.random.default_rng(np.random.SeedSequence([seed,sid,tid,i]))
        x1,x2=group(n1,rng,scenario,False),group(n2,rng,scenario,True)
        rows.append({"replicate":i,"python":python_reference(x1,x2),"wlsmv":reference(x1,x2)})
    return summarize_cell(sid,scenario,seed,offset,rows)

def summarize_cell(sid,scenario,seed,offset,rows):
    n1,n2=SIZES[sid]
    if not rows or [r["replicate"] for r in rows]!=list(range(offset,offset+len(rows))):
        raise ValueError("Missing or duplicate replicate indices")
    both=[r for r in rows if r["python"]["status"]==r["wlsmv"]["status"]=="PROPER"]
    same=sum(set(r["python"]["decision"]["rejected_tests"])==set(r["wlsmv"]["decision"]["rejected_tests"]) for r in both)
    per_test={}
    for name in NAMES:
        outcomes=[(name in r["python"]["decision"]["rejected_tests"],
                   name in r["wlsmv"]["decision"]["rejected_tests"]) for r in both]
        per_test[name]={"both_reject":sum(a and b for a,b in outcomes),
                        "python_only":sum(a and not b for a,b in outcomes),
                        "wlsmv_only":sum(b and not a for a,b in outcomes),
                        "neither":sum(not a and not b for a,b in outcomes)}
    reference_blocked = all(r["wlsmv"].get("reason") == "Independent Python ordinal reference not established" for r in rows)
    return {"schema":"p05-python-invariance-development-v1" if reference_blocked else "p05-paired-invariance-v2",
            "independent_reference_verified":False,"sizes":[n1,n2],"scenario":scenario,
            "true_nulls":list(TRUE_NULLS[scenario]),"requested":len(rows),
            "offset":offset,"seed":seed,"python":summarize(rows,scenario,"python"),
            "wlsmv":summarize(rows,scenario,"wlsmv"),"paired_available":len(both),
            "paired_identical_rejection_sets":rate(same,len(both)),
            "paired_test_decisions":per_test,"records":rows}

def aggregate(parts,expected):
    if not parts or expected<1:raise ValueError("Empty calibration or denominator")
    key=lambda p:(p.get("schema"),tuple(p["sizes"]),p["scenario"],p["seed"])
    meta=key(parts[0])
    if meta[0] not in ("p05-paired-invariance-v2","p05-python-invariance-development-v1") or any(key(p)!=meta for p in parts):
        raise ValueError("Mixed shard metadata")
    if meta[1] not in SIZES or meta[2] not in SCENARIOS:
        raise ValueError("Unknown cell")
    for p in parts:
        if p["requested"]!=len(p["records"]) or [r["replicate"] for r in p["records"]]!=list(range(p["offset"],p["offset"]+p["requested"])):
            raise ValueError("Corrupt shard accounting")
    rows=sorted((r for p in parts for r in p["records"]),key=lambda r:r["replicate"])
    if len(rows)!=expected:raise ValueError("Incomplete aggregate")
    out=summarize_cell(SIZES.index(meta[1]),meta[2],meta[3],0,rows)
    out["precision_screen_only"]=expected<2000
    return out


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reps",type=int,default=1);p.add_argument("--seed",type=int,default=20261209)
    p.add_argument("--offset",type=int,default=0);p.add_argument("--smoke",action="store_true")
    p.add_argument("--size-index",type=int,choices=range(len(SIZES)))
    p.add_argument("--scenario",choices=SCENARIOS)
    p.add_argument("--aggregate",type=Path,help="Folder of single-cell shard JSON files")
    p.add_argument("--expected",type=int,help="Required complete independent outer denominator")
    a=p.parse_args()
    if a.aggregate:
        if a.expected is None or a.smoke or a.scenario is not None or a.size_index is not None:
            p.error("Aggregation requires --expected only, with one cell per folder")
        parts=[json.loads(path.read_text(encoding="utf-8")) for path in sorted(a.aggregate.glob("shard-*.json"))]
        if any(len(part["cells"])!=1 for part in parts):p.error("Each shard must contain exactly one cell")
        print(json.dumps(aggregate([part["cells"][0] for part in parts],a.expected),indent=2,allow_nan=False))
        raise SystemExit(0)
    if (a.size_index is None)!=(a.scenario is None) or (a.smoke and a.scenario is not None):
        p.error("Specify both cell arguments, or --smoke")
    grid=[(0,"invariant"),(1,"loading_dif"),(2,"threshold_dif"),(3,"intercept_dif")] if a.smoke else [(i,s) for i in range(4) for s in SCENARIOS]
    if a.scenario is not None:grid=[(a.size_index,a.scenario)]
    cells=[cell(i,s,a.reps,a.seed,a.offset) for i,s in grid]
    print(json.dumps({"synthetic":True,"reference":"BLOCKED: independent Python ordinal reference not established",
        "confirmatory_authorized":False,"latent_mean_comparison_authorized":False,"cells":cells},indent=2,allow_nan=False))
    if not any(c["python"]["available"]["count"] for c in cells):p.exit(1,"No usable Python development family\n")
