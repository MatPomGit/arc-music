"""Lossless import of candidate P06 empirical CSV ledgers, no authorization."""
import csv
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).parent
BOOL={"True":True,"true":True,"False":False,"false":False}
BOOL_FIELDS={"eligible_first","activity_defined","activity_relevant","activity_completed","technical_failure"}
STRING_FIELDS={"participant_id","session_id","activity_id","followup_activity_id","local_day",
               "first_day","withdrawal_day","timezone","withdrawal_time","checkin_time",
               "pre_time","start_time","end_time","post_time","followup_time",
               "activity_status_reason","followup_missing_reason",*BOOL_FIELDS}

def fields(kind):
    if kind=="sessions":
        with (ROOT/"data-dictionary.csv").open(newline="",encoding="utf-8") as f:
            return {r["field"] for r in csv.DictReader(f)}
    if kind in ("enrollment","checkins"):
        with (ROOT/"daily-data-dictionary.csv").open(newline="",encoding="utf-8") as f:
            return {r["field"] for r in csv.DictReader(f) if r["file"]==kind}
    raise ValueError("Unknown export kind")

def read_export(path,kind,*,empirical=False):
    expected=fields(kind)
    with open(path,newline="",encoding="utf-8-sig") as f:
        header=next(csv.reader(f),[])
    if not header or len(header)!=len(set(header)):
        raise ValueError("Missing or duplicate CSV fields")
    if empirical and set(header)!=expected:
        raise ValueError("Empirical export field mismatch: "+kind)
    d=pd.read_csv(path,encoding="utf-8-sig",dtype={k:"string" for k in STRING_FIELDS},
                  keep_default_na=False,na_values=["","NA"])
    for k in BOOL_FIELDS & set(d):
        if not d[k].dropna().isin(BOOL).all():
            raise ValueError("Invalid flag: "+k)
        # Native bool for known values, np.nan for unknown, compatible with
        # legacy ledger operations while preserving each of the three states.
        d[k]=d[k].map(BOOL)
    return d
