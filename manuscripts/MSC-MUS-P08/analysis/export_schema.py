"""Lossless P08 CSV import. Strict empirical contract; legacy synthetic schema retained."""
import csv
import re
import pandas as pd
from assignment_ledger import VERSION,ID,DIGEST
from inference import BASE,ITEMS

ASSIGNMENT=("participant_id","authority","manual","training","randomised_at",
            "bank_digest","system_schedule","schema_version")
FIELDS=(*ASSIGNMENT,*[k for k in BASE if k!="training"],"heard_version",
        *ITEMS["ownership"],*ITEMS["agency"])
STRING_FIELDS=("participant_id","bank_digest","system_schedule","schema_version",
               "randomised_at","heard_version")
BOOLEAN={"True":True,"true":True,"False":False,"false":False}

def read_export(path,*,empirical=False):
    # Check the literal header before pandas can rename duplicate column names.
    with open(path,newline="",encoding="utf-8-sig") as f:
        header=next(csv.reader(f),[])
    if not header or len(header)!=len(set(header)):
        raise ValueError("Missing or duplicate CSV fields")
    if empirical and set(header)!=set(FIELDS):
        raise ValueError("Empirical export field mismatch")
    d=pd.read_csv(path,encoding="utf-8-sig",dtype={k:"string" for k in STRING_FIELDS},
                  keep_default_na=False,na_values=["","NA"])
    if "heard_version" not in d or not d.heard_version.dropna().isin(BOOLEAN).all():
        raise ValueError("Invalid heard flag")
    d["heard_version"]=d.heard_version.map(BOOLEAN).astype("boolean")
    if empirical:
        if not d.participant_id.map(lambda x:isinstance(x,str) and ID.fullmatch(x) is not None).all():
            raise ValueError("Invalid opaque identifier")
        if not d.bank_digest.map(lambda x:isinstance(x,str) and DIGEST.fullmatch(x) is not None).all():
            raise ValueError("Invalid bank digest")
        if not d.system_schedule.map(lambda x:isinstance(x,str) and re.fullmatch(r"[01]{4}",x) is not None).all():
            raise ValueError("Invalid system schedule")
        if not d.schema_version.eq(VERSION).fillna(False).all():
            raise ValueError("Invalid schema version")
    return d
