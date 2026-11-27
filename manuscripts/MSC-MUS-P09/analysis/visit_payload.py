"""Canonical minimal numeric visit payload, for synthetic offline ledger tests.

No personal event text or contact data. The restricted candidate database is
not an approved retention service. Missing visits cannot self-attest a
defined endpoint without a separate approved ascertainment mechanism.
"""
import json
from numbers import Real
import math
import numpy as np
import pandas as pd

def visit_fields(j):
    if j not in (1,2):raise ValueError("Invalid visit")
    return (f"same_event{j}",f"target_status{j}",
            *(f"understanding{j}{k}" for k in (1,2,3)),
            *(("distance1",) if j==1 else ()))

def missing(v):
    return v is None or v is pd.NA or (isinstance(v,Real) and math.isnan(float(v)))

def canonical(j,payload):
    names=visit_fields(j)
    if not isinstance(payload,dict) or set(payload)!=set(names):
        raise ValueError("Visit payload field mismatch")
    result={}
    same=payload[names[0]]
    if not missing(same) and not isinstance(same,(bool,np.bool_)):
        raise ValueError("Invalid event flag")
    result[names[0]]=None if missing(same) else bool(same)
    status=payload[names[1]]
    if not isinstance(status,str) or status not in ("defined","undefined","unknown"):
        raise ValueError("Invalid target status")
    result[names[1]]=status
    for field in names[2:]:
        value=payload[field]
        if missing(value):
            result[field]=None
        elif (isinstance(value,(bool,np.bool_)) or not isinstance(value,Real)
              or not math.isfinite(float(value)) or not 0<=value<=10 or int(value)!=value):
            raise ValueError("Invalid visit score: "+field)
        else:
            result[field]=int(value)
    if result[names[0]] is True and status!="defined" and any(result[k] is not None for k in names[2:]):
        raise ValueError("Same-event score contradicts target status")
    return json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)

def empty_visit(j,row):
    names=visit_fields(j)
    return (isinstance(row[names[1]],str) and row[names[1]]=="unknown"
            and all(missing(row[k]) for k in (names[0],*names[2:])))
