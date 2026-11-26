"""Distinguish planned windows, missed responses and cessation of collection.

Only use records approved for retention by the institution. A cessation log is
not an authorization to retain data after a request for deletion.
"""
import pandas as pd
from datetime import datetime

TIMES=["baseline_time","exposure_time","followup60_time","followup180_time"]

def utc(value):
    if pd.isna(value):return pd.NaT
    dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if dt.utcoffset() is None:raise ValueError("Timezone offset required")
    return pd.Timestamp(dt).tz_convert("UTC")

def apply_withdrawal(frame,events):
    if not {"participant_id","withdrawal_time"}<=set(events):
        raise ValueError("Missing withdrawal columns")
    d=frame.copy();e=events.copy()
    if e.participant_id.isna().any():raise ValueError("Missing withdrawal participant")
    e["participant_id"]=e.participant_id.astype(str)
    if e.participant_id.duplicated().any():raise ValueError("Duplicate withdrawal event")
    if not set(e.participant_id)<=set(d.participant_id.astype(str)):raise ValueError("Unknown withdrawal participant")
    e["withdrawal_time"]=pd.to_datetime(e.withdrawal_time.map(utc),utc=True)
    if e.withdrawal_time.isna().any():raise ValueError("Missing withdrawal time")
    cut=pd.to_datetime(d.participant_id.astype(str).map(e.set_index("participant_id").withdrawal_time),utc=True)
    start=pd.to_datetime(d.scheduled_time.map(utc),utc=True)
    d["withdrawn_before_prompt"]=cut.notna() & start.ge(cut)
    for col in TIMES:
        if col not in d:continue
        stamp=pd.to_datetime(d[col].map(utc),utc=True)
        if (cut.notna() & stamp.ge(cut)).any():
            raise ValueError("Response timestamp at or after withdrawal")
    if "response_record_received" in d:
        if (d.withdrawn_before_prompt & d.response_record_received).any():
            raise ValueError("Response record for cancelled window")
    d["withdrawal_during_window"]=cut.notna() & start.lt(cut) & (start+pd.Timedelta(minutes=210)).gt(cut)
    return d

def summarize(d):
    active=d.loc[~d.withdrawn_before_prompt]
    return {"planned_windows":len(d),"active_prompt_windows":len(active),
            "cancelled_after_withdrawal":int(d.withdrawn_before_prompt.sum()),
            "withdrawal_during_possible_window":int(d.withdrawal_during_window.sum()),
            "active_valid_baselines":int(active.baseline_valid.sum()),
            "active_valid_baseline_rate":float(active.baseline_valid.mean()) if len(active) else None,
            "active_complete_h1":int(active.h1_valid.sum()),
            "active_complete_h1_rate":float(active.h1_valid.mean()) if len(active) else None}
