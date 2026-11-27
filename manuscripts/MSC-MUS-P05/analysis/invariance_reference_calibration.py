"""Paired eight-item WLSMV and Python ordinal diagnostics on identical synthetic inputs."""
import argparse,csv,hashlib,json,math,subprocess,tempfile
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
    x=np.vstack((np.column_stack((np.ones(len(x1),int),x1)),
                 np.column_stack((np.full(len(x2),2,int),x2))))
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp); inp,out=path/"synthetic.csv",path/"tests.csv"
        np.savetxt(inp,x,fmt="%d",delimiter=",",header="group,"+",".join(f"item{i+1}" for i in range(8)),comments="")
        sha=hashlib.sha256(inp.read_bytes()).hexdigest()
        try:
            proc=subprocess.run(["Rscript",str(Path(__file__).with_name("invariance_reference.R")),str(inp),str(out)],
                capture_output=True,text=True,check=True,timeout=300)
            with out.open(newline="",encoding="utf-8") as f: rows=list(csv.DictReader(f))
            if [r["test"] for r in rows]!=list(NAMES):raise ValueError("Invalid reference test slots")
            for row in rows:
                if row["status"] not in ("PROPER","IMPROPER","NONCONVERGED","ERROR","UNAVAILABLE"):
                    raise ValueError("Unknown reference status")
                for k in ("p_value","df"):
                    row[k]=float(row[k]) if row[k] not in ("","NA","NaN") else None
                if row["status"]=="PROPER" and (row["p_value"] is None or
                    not math.isfinite(row["p_value"]) or not 0<=row["p_value"]<=1 or
                    row["df"] is None or not math.isfinite(row["df"]) or row["df"]<=0):
                    raise ValueError("Invalid available reference statistic")
            if not all(r["status"]=="PROPER" for r in rows):
                return {"status":"UNAVAILABLE","input_sha256":sha,"tests":rows}
            decision=global_decision([r["p_value"] for r in rows[:2]],
                         {r["test"]:{"p_value":r["p_value"]} for r in rows[2:]})
            return {"status":"PROPER","input_sha256":sha,"tests":rows,"decision":decision}
        except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:
            return {"status":"ERROR","input_sha256":sha,"reason":str(exc)}

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
    both=[r for r in rows if r["python"]["status"]==r["wlsmv"]["status"]=="PROPER"]
    same=sum(r["python"]["decision"]["rejected_tests"]==r["wlsmv"]["decision"]["rejected_tests"] for r in both)
    return {"sizes":[n1,n2],"scenario":scenario,"true_nulls":list(TRUE_NULLS[scenario]),"requested":reps,
            "offset":offset,"seed":seed,"python":summarize(rows,scenario,"python"),
            "wlsmv":summarize(rows,scenario,"wlsmv"),"paired_available":len(both),
            "paired_identical_rejection_sets":rate(same,len(both)),"records":rows}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reps",type=int,default=1);p.add_argument("--seed",type=int,default=20261209)
    p.add_argument("--offset",type=int,default=0);p.add_argument("--smoke",action="store_true")
    a=p.parse_args()
    grid=[(0,"invariant"),(1,"loading_dif"),(2,"threshold_dif"),(3,"intercept_dif")] if a.smoke else [(i,s) for i in range(4) for s in SCENARIOS]
    cells=[cell(i,s,a.reps,a.seed,a.offset) for i,s in grid]
    print(json.dumps({"synthetic":True,"reference":"WLSMV theta Wu.Estabrook.2016",
        "confirmatory_authorized":False,"latent_mean_comparison_authorized":False,"cells":cells},indent=2,allow_nan=False))
    if any(c["wlsmv"]["status_counts"]["ERROR"] for c in cells):p.exit(1,"Reference execution error\n")
    if not any(c["wlsmv"]["available"]["count"] for c in cells):p.exit(1,"No usable reference family\n")
