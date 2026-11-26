"""Reproduce historical numerical tables; report differences without hiding failures."""
import argparse
import csv
import json
from pathlib import Path
import math
import platform
import numpy as np
import scipy
from cluster_calibration import calibrate
from stress import run as stress_run
from missing_calibration import run as missing_run

ROOT=Path(__file__).resolve().parent

def compare_rows(path, actual, keys):
    with open(path,encoding="utf-8",newline="") as handle:
        expected=list(csv.DictReader(handle))
    def key(row):
        return tuple(str(float(row[k])) if k not in ("mechanism","missingness") else str(row[k]) for k in keys)
    index={key(r):r for r in actual}
    if len(index)!=len(actual):
        raise ValueError("Duplicate reproduced scenario")
    differences=[]
    seen=set()
    for row in expected:
        k=key(row)
        if k in seen: raise ValueError("Duplicate historical scenario")
        seen.add(k)
        if k not in index:
            differences.append({"scenario":k,"error":"missing reproduced scenario"})
            continue
        for field,s in row.items():
            if field in keys: continue
            if field not in index[k]:
                differences.append({"scenario":k,"field":field,"error":"missing value"})
                continue
            val=float(s); got=float(index[k][field])
            # Compare at the precision displayed in the historical CSV.
            places=len(s.split(".")[1]) if "." in s else 0
            tol=.5*10**(-places)+1e-10
            if not math.isfinite(got) or abs(val-got)>tol:
                differences.append({"scenario":k,"field":field,"historical":val,"reproduced":got,"rounding_tolerance":tol})
    for k in index.keys()-seen:
        differences.append({"scenario":k,"error":"unexpected reproduced scenario"})
    return {"historical_rows":len(expected),"reproduced_rows":len(actual),
            "mismatch_count":len(differences),"differences":differences}

def run(kind, output):
    if kind=="cluster":
        raw=calibrate()
        rows=[dict(latent_slope=c["latent"],n=c["n"],missingness=c["scenario"],bias_rounded=c["bias"],
                   full_rejection=c["full"]["rejection"],full_coverage=c["full"]["coverage"],
                   nested_rejection=c["nested"]["rejection"],nested_coverage=c["nested"]["coverage"]) for c in raw["cells"]]
        comparison=compare_rows(ROOT/"cluster-calibration-results.csv",rows,["latent_slope","n","missingness"])
    elif kind=="stress":
        raw=stress_run()
        rows=[dict(sessions=c["m"],beta=c["beta"],mechanism=c["kind"],dropout=c["drop"],
                   full_rejection=c["full"]["rejection"],nested_rejection=c["nested"]["rejection"],
                   bias_rounded=c["bias"],retention_rounded=c["retention"]) for c in raw["cells"]]
        comparison=compare_rows(ROOT/"stress-results.csv",rows,["sessions","beta","mechanism","dropout"])
    elif kind=="missing":
        raw=missing_run()
        rows=[]
        for c in raw["cells"]:
            r={k:c[k] for k in ["beta","missing","mechanism","valid","failures"]}
            for name in ["cc","ipw10","ipw20"]:
                for metric in ["bias","rmse"]:
                    r[name+"_"+metric]=c["estimators"][name][metric]
            r.update(envelope_fraction=c["envelope"],envelope_width=c["width"])
            rows.append(r)
        comparison=compare_rows(ROOT/"missing-calibration-results.csv",rows,["beta","missing","mechanism"])
    else: raise ValueError("Unknown calibration")
    report={"kind":kind,"environment":{"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__},
            "status":"MATCH" if comparison["mismatch_count"]==0 else "MISMATCH",
            "comparison":comparison,"results":raw}
    Path(output).write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({"kind":kind,"status":report["status"],"mismatch_count":comparison["mismatch_count"]}))
    return report["status"]=="MATCH"

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("kind",choices=["cluster","stress","missing"])
    p.add_argument("--output",required=True)
    a=p.parse_args()
    raise SystemExit(0 if run(a.kind,a.output) else 1)
