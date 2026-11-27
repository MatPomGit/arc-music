"""P04 validated empirical entry point. Low-level helpers remain synthetic interfaces."""
import argparse
import csv
import json
import re
from pathlib import Path
import numpy as np
from paq_scoring import validate_total, score, describe_scores
from inference import composite, design, analyze
from secondary import secondary
from exploratory import spline_sensitivity

TOKEN = re.compile(r"p04-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
ITEMS = tuple(f"paq_s_item_{i}" for i in range(1,7))
CORE = ("study_token","assignment","expression_ease","clarity_t0","distress_t0",
        "prior_ai_music","scenario_mode","meaningful_sketch","fit_t1","clarity_t1",
        "fit_missing_reason")
OPTIONAL = ("paq_s_total",*ITEMS,"expressive_success","agency_t1","distress_t1",
            "clarity_t2","completed","suggestions_used")


def numeric(v,lo,hi,missing=False):
    if v is None or (isinstance(v,str) and v in ("","NA")):
        if missing:
            return np.nan
        raise ValueError("Required numeric field missing")
    if isinstance(v,(bool,np.bool_)):
        raise ValueError("Boolean is not a numeric rating")
    try:
        v=float(v)
    except (TypeError,ValueError):
        raise ValueError("Invalid numeric field") from None
    if missing and np.isnan(v):
        return v
    if not np.isfinite(v) or not lo<=v<=hi or v!=np.floor(v):
        raise ValueError("Invalid integer field or range")
    return v


def token(v):
    if not isinstance(v,str) or not TOKEN.fullmatch(v):
        raise ValueError("Invalid P04 study token")
    return v


def cohort(rows,ledger):
    assigned={}
    for row in ledger:
        if set(row)!={"study_token","assignment"}:
            raise ValueError("Ledger requires token and assignment only")
        key=token(row["study_token"])
        if key in assigned:
            raise ValueError("Duplicate ledger token")
        assigned[key]=numeric(row["assignment"],0,1)
    if set(assigned.values())!={0.,1.} or not rows:
        raise ValueError("Both assigned arms and cohort required")
    keys=set(rows[0])
    if not set(CORE)<=keys or not keys<=set(CORE+OPTIONAL):
        raise ValueError("Unexpected or missing cohort columns")
    items=set(ITEMS)&keys
    if items and items!=set(ITEMS):
        raise ValueError("Provide all six item columns or none")
    if not items and "paq_s_total" not in keys:
        raise ValueError("Complete PAQ-S total or six items required")
    seen=set(); records=[]
    for row in rows:
        if set(row)!=keys:
            raise ValueError("Inconsistent row schema")
        key=token(row["study_token"])
        if key in seen or key not in assigned:
            raise ValueError("Duplicate or unknown cohort token")
        seen.add(key)
        arm=numeric(row["assignment"],0,1)
        if arm!=assigned[key]:
            raise ValueError("Assignment mismatch")
        if items:
            total=float(score([[numeric(row[k],1,7) for k in ITEMS]])["total"][0])
            if "paq_s_total" in keys and numeric(row["paq_s_total"],6,42)!=total:
                raise ValueError("PAQ-S total disagrees with six items")
        else:
            total=numeric(row["paq_s_total"],6,42)
        validate_total([total])
        scenario=row["scenario_mode"]
        if scenario not in ("personal_mild","fictional"):
            raise ValueError("Unknown scenario mode")
        cov=[numeric(row[k],0,10) for k in ("expression_ease","clarity_t0","distress_t0")]
        cov += [numeric(row["prior_ai_music"],0,1),float(scenario=="fictional")]
        status=numeric(row["meaningful_sketch"],0,1,True)
        fit=numeric(row["fit_t1"],0,10,True)
        value=float(composite([fit],[status])[0])
        expected=("undefined",) if status==0 else (("","NA",None) if np.isfinite(fit)
                  else ("unavailable","withdrawn"))
        if row["fit_missing_reason"] not in expected:
            raise ValueError("Fit missing reason contradicts sketch/rating state")
        if "expressive_success" in keys:
            supplied=numeric(row["expressive_success"],0,10,True)
            if not (supplied==value or (np.isnan(supplied) and np.isnan(value))):
                raise ValueError("Supplied composite contradicts derived endpoint")
        for k in ("agency_t1","distress_t1","clarity_t2","completed","suggestions_used"):
            if k in keys:
                numeric(row[k],0,1 if k in ("completed","suggestions_used") else 10,True)
        records.append((key,arm,total,cov,status,fit,value,numeric(row["clarity_t1"],0,10,True)))
    if seen!=set(assigned):
        raise ValueError("Cohort does not reconcile with assignment ledger")
    records.sort(key=lambda x:x[0])
    return tuple(np.asarray([r[i] for r in records],float) for i in range(1,8))


def component_flow(a,s,f,y):
    result={}
    for arm in (0,1):
        q=a==arm
        present=q&(s==1); rated=present&np.isfinite(f)
        result[str(arm)]={"assigned":int(q.sum()),"confirmed_meaningful":int(present.sum()),
            "confirmed_absent":int((q&(s==0)).sum()),"unknown_status":int((q&np.isnan(s)).sum()),
            "meaningful_rating_missing":int((present&np.isnan(f)).sum()),
            "fit_rated":int(rated.sum()),"fit_mean_descriptive":float(f[rated].mean()) if rated.any() else None,
            "composite_available":int((q&np.isfinite(y)).sum())}
    return result


def safe(fn):
    try:
        return fn()
    except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
        return {"available":False,"reason":str(exc)}


def run(rows,ledger,m=50,seed=20261126):
    a,d,c,s,f,y,q=cohort(rows,ledger)
    x=design(a,d,c)
    return {"schema":"p04-cohort-v1","n_assigned":len(a),"confirmatory_authorized":False,
            "paq_s_total":describe_scores(d),"component_flow":component_flow(a,s,f,y),
            "component_interpretation":"conditional fit is descriptive, not a causal contrast",
            "H1":safe(lambda:analyze(x,y,m,seed)),
            "secondary":safe(lambda:secondary(a,d,c,q,m,seed)),
            "exploratory":safe(lambda:spline_sensitivity(a,d,c,y,m,seed))}


def read_csv(path):
    with open(path,encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames):
            raise ValueError("Missing or repeated column names")
        rows=list(reader)
        if any(None in r or any(v is None for v in r.values()) for r in rows):
            raise ValueError("Malformed CSV row")
        return rows


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("cohort",type=Path)
    p.add_argument("--ledger",type=Path,required=True)
    p.add_argument("--data-kind",choices=["synthetic","empirical"],required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--m",type=int,default=50)
    args=p.parse_args()
    result=run(read_csv(args.cohort),read_csv(args.ledger),m=args.m)
    result["data_kind"]=args.data_kind
    args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
