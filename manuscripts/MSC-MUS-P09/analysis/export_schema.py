"""Single P09 export contract for authorized offline records."""
import pandas as pd

VERSION="p09-export-v2"
ASSIGNMENT=("participant_id","training","music","randomised_at","bank_digest","schema_version")
EVENTS=("task_started_at","task_ended_at","task_end_reason","t1_at","t2_at")
BASE=("prior_use_days","importance0","understanding01","understanding02","understanding03","distance0")
OUTCOMES=("same_event1","same_event2","target_status1","target_status2",
          "understanding11","understanding12","understanding13","understanding21",
          "understanding22","understanding23","distance1")
FIELDS=ASSIGNMENT+EVENTS+BASE+OUTCOMES

def instant(value):
    if pd.isna(value):return None
    t=pd.Timestamp(value)
    if t.tzinfo is None:raise ValueError("Timestamp offset required")
    return t.tz_convert("UTC")

def validate_fields(frame):
    if set(frame)!=set(FIELDS) or frame.columns.duplicated().any():
        raise ValueError("Export schema field mismatch")
    if not frame.schema_version.eq(VERSION).fillna(False).all():
        raise ValueError("Export schema version mismatch")
    if not frame.bank_digest.map(lambda v:isinstance(v,str) and len(v)==64 and all(c in "0123456789abcdef" for c in v)).all():
        raise ValueError("Invalid bank digest")
    for j in (1,2):
        fields=[f"same_event{j}",*[f"understanding{j}{k}" for k in (1,2,3)]]
        if j==1:fields.append("distance1")
        if (frame[f"t{j}_at"].isna() & frame[fields].notna().any(axis=1)).any():
            raise ValueError("Outcome payload without authoritative submission")
    return True


def read_export(path):
    """Preserve opaque identifiers/digests; parse Boolean tokens independently."""
    d=pd.read_csv(path,dtype={k:"string" for k in ("participant_id","bank_digest","schema_version","same_event1","same_event2")},keep_default_na=False,na_values=["","NA"])
    for k in ("same_event1","same_event2"):
        if k not in d:raise ValueError("Missing event flag")
        if not d[k].dropna().isin(("True","False","true","false")).all():
            raise ValueError("Invalid event flag")
        d[k]=d[k].map({"True":True,"true":True,"False":False,"false":False}).astype("boolean")
    validate_fields(d)
    return d
