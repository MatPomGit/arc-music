"""Reanalyse archived fits or run independent paired global-gate calibration."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
from collections import Counter
import math
from invariance_family import global_decision

TARGET = {"threshold_dif":"threshold_shape","loading_dif":"threshold_loading",
          "intercept_dif":"threshold_loading_intercept"}


def rate(k,n):
    if not n:
        return {"count":k,"denominator":n,"rate":None,"mcse":None,"mc_interval":None}
    p=k/n
    z=1.959963984540054
    centre=(p+z*z/(2*n))/(1+z*z/n)
    radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return {"count":k,"denominator":n,"rate":p,"mcse":math.sqrt(p*(1-p)/n),
            "mc_interval":[max(0.,centre-radius),min(1.,centre+radius)]}


def summarize(cell):
    rows=cell["records"]
    n=len(rows)
    if n != cell["requested"] or not n or len({r["replicate"] for r in rows}) != n:
        raise ValueError("replication accounting mismatch")
    if any(r["status"] not in ("proper","failure") for r in rows):
        raise ValueError("invalid replication status")
    proper=[r for r in rows if r["status"]=="proper"]
    decisions=[global_decision(r["configural_p_values"],r["tests"]) for r in proper]
    rejects=sum(d["any_rejected"] for d in decisions)
    target=TARGET.get(cell["scenario"])
    detected=sum(target in d["rejected_tests"] for d in decisions) if target else None
    return {"sizes":cell["sizes"],"scenario":cell["scenario"],"requested":n,
            "proper":len(proper),"failure":n-len(proper),
            "failure_reasons":dict(Counter(r.get("reason","unspecified") for r in rows if r["status"]=="failure")),
            "legacy_any_rejection":rate(sum(r["any_gate_rejected"] for r in proper),n),
            "holm_any_operational":rate(rejects,n),"holm_any_conditional":rate(rejects,len(proper)),
            "holm_target_operational":rate(detected,n) if target else None,
            "holm_target_conditional":rate(detected,len(proper)) if target else None,
            "first_gate_counts":dict(Counter(d["ordered_gate"] for d in decisions)),
            "records":[{"replicate":r["replicate"],**d} for r,d in zip(proper,decisions)]}


def run(reps=20,seed=20261202,offset=0):
    from invariance_power import run as fit
    raw=fit(reps,seed,offset)
    return {"synthetic":True,"rule":"holm_five_v1","seed":seed,"offset":offset,
            "source":"independent simulated data","scenarios":[summarize(c) for c in raw["scenarios"]]}


def archived(path):
    with ZipFile(path) as z:
        raw=z.read("p05-invariance-power.json")
    data=json.loads(raw)
    return {"synthetic":True,"rule":"holm_five_v1","seed":data["seed"],
            "source":"paired archived fits, not independent validation",
            "archive_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "scenarios":[summarize(c) for c in data["scenarios"]]}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path)
    p.add_argument("--reps",type=int,default=20)
    p.add_argument("--seed",type=int,default=20261202)
    p.add_argument("--offset",type=int,default=0)
    a=p.parse_args()
    print(json.dumps(archived(a.archive) if a.archive else run(a.reps,a.seed,a.offset),
                     indent=2,allow_nan=False))
