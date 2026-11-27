"""Independent EFA/CFA development screens of competing AI-MRFS structures."""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import tempfile
import numpy as np
from recovery import simulate
from factor_count_calibration import assess
from robust_calibration import wilson

MODELS = ("one_factor", "correlated_seven", "higher_order")
METRICS = ("minimum_uniqueness", "minimum_factor_eigenvalue", "cfi_scaled",
           "tli_scaled", "rmsea_scaled", "srmr", "p_scaled")
STATUSES = ("PROPER", "IMPROPER", "NONCONVERGED", "ERROR", "INSUFFICIENT_COMPLETE")


def reference(x):
    complete = x[np.isfinite(x).all(axis=1)]
    if len(complete) <= 35 or any(len(np.unique(c)) != 5 for c in complete.T):
        return [{"model":m,"status":"INSUFFICIENT_COMPLETE","n":len(complete)} for m in MODELS]
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp)
        inp, out = path/"synthetic.csv", path/"models.csv"
        np.savetxt(inp, complete, delimiter=",", fmt="%d",
                   header=",".join(f"item{i+1}" for i in range(35)), comments="")
        digest = hashlib.sha256(inp.read_bytes()).hexdigest()
        try:
            subprocess.run(["Rscript",str(Path(__file__).with_name("model_reference.R")),
                            str(inp),str(out)], capture_output=True,text=True,check=True,timeout=600)
            with out.open(newline="",encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            if [x["model"] for x in rows] != list(MODELS):
                raise ValueError("Reference output must report all three models")
            for row in rows:
                if row["status"] not in STATUSES:
                    raise ValueError("Unknown reference fit status")
                row["n"] = int(row["n"])
                row["input_sha256"] = digest
                for metric in METRICS:
                    v = row[metric]
                    row[metric] = float(v) if v not in ("NA","NaN","Inf","-Inf","") else None
            return rows
        except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:
            return [{"model":m,"status":"ERROR","n":len(complete),
                     "input_sha256":digest,"reason":str(exc)} for m in MODELS]


def summary(rows):
    if not rows:
        raise ValueError("No replications")
    result = {}
    for model in MODELS:
        fits = [next(x for x in row["cfa"] if x["model"]==model) for row in rows]
        proper = [x for x in fits if x["status"]=="PROPER"]
        n = len(fits)
        rate = len(proper)/n
        result[model] = {"requested":n,"proper":len(proper),"proper_rate":rate,
                         "proper_interval":wilson(len(proper),n),
                         "proper_mcse":float(np.sqrt(rate*(1-rate)/n)),
                         "status_counts":{s:sum(x["status"]==s for x in fits) for s in STATUSES},
                         "fit_metrics_proper_only":{
                             m:float(np.mean([x[m] for x in proper if x.get(m) is not None]))
                             if any(x.get(m) is not None for x in proper) else None for m in METRICS}}
    return result


def cell(n, loading, rho, skew, missing, reps, pa_reps, seed):
    rows = []
    for i in range(reps):
        # Independent EFA and CFA samples, never select a model on the CFA draw.
        e, c, pa = np.random.SeedSequence([seed,i]).spawn(3)
        efa = simulate(n,7,5,loading,rho,skew,missing,np.random.default_rng(e))
        cfa = simulate(n,7,5,loading,rho,skew,missing,np.random.default_rng(c))
        rows.append({"replicate":i,
                     "efa":assess(efa,7,5,loading,pa_reps,int(pa.generate_state(1)[0])),
                     "cfa":reference(cfa)})
    return {"n_efa":n,"n_cfa":n,"loading":loading,"rho":rho,"skew":skew,
            "item_mcar":missing,"requested":reps,"pa_reps":pa_reps,
            "seed":seed,"reference_summary":summary(rows),
            "efa_joint_recovery":sum(x["efa"]["joint_recovery"] for x in rows),
            "records":rows}


def run(reps=2,pa_reps=20,smoke=False,seed=20261130):
    if reps<1 or pa_reps<10:
        raise ValueError("Invalid replication count")
    grid = [(500,.65,.35,False,0.),(500,.40,.80,True,0.)]
    if not smoke:
        grid += [(n,l,r,True,m) for n,(l,r),m in itertools.product(
            (500,800),((.65,.35),(.40,.80)),(.02,.10,.20))]
    return {"synthetic":True,"model_selection_authorized":False,
            "note":"EFA/CFA independent samples; complete-case sensitivity only; no empirical model selection",
            "cells":[cell(*g,reps,pa_reps,seed+i) for i,g in enumerate(grid)]}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reps",type=int,default=2)
    p.add_argument("--pa-reps",type=int,default=20)
    p.add_argument("--smoke",action="store_true")
    p.add_argument("--seed",type=int,default=20261130)
    a=p.parse_args()
    print(json.dumps(run(a.reps,a.pa_reps,a.smoke,a.seed),indent=2,allow_nan=False))
