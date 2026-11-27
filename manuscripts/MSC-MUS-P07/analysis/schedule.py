"""Frozen EMA schedule and authoritative denominator reconciliation.

Use opaque study IDs, not names. No network or notifications.
"""
import argparse
import hashlib
import hmac
from datetime import date,datetime,time,timedelta,timezone
from zoneinfo import ZoneInfo
import pandas as pd
import numpy as np

UTC=timezone.utc
KEYS=["participant_id","window_id","study_day","scheduled_time","local_day","timezone"]
RESPONSE=["baseline_time","exposure_time","followup60_time","followup180_time",
          "creation_ongoing","creation_first_hour","valence0","arousal0",
          "intention0","desired_arousal0","valence60","arousal60","valence180","arousal180","later_creation"]

def local_instant(day,minute,zone):
    naive=datetime.combine(day,time(minute//60,minute%60))
    a=naive.replace(tzinfo=zone,fold=0)
    b=naive.replace(tzinfo=zone,fold=1)
    if a.utcoffset()!=b.utcoffset() or a.astimezone(UTC).astimezone(zone).replace(tzinfo=None)!=naive:
        raise ValueError("Ambiguous or nonexistent local time")
    return a

def minute(v):
    s=str(v)
    t=time.fromisoformat(s)
    if t.isoformat(timespec="minutes")!=s or t.second or t.microsecond or t.tzinfo:
        raise ValueError("Use HH:MM for availability")
    return t.hour*60+t.minute

def generate(enrollment,seed):
    required={"participant_id","first_day","timezone","available_from","available_until"}
    if not required<=set(enrollment):raise ValueError("Missing enrollment columns")
    if enrollment.empty:raise ValueError("Empty enrollment")
    if enrollment.participant_id.isna().any():raise ValueError("Missing participant")
    ids=enrollment.participant_id.astype(str)
    if ids.str.strip().eq("").any() or ids.duplicated().any():raise ValueError("Invalid or duplicate participant")
    key=str(seed).encode("utf-8")
    rows=[]
    for r in enrollment.assign(participant_id=ids).itertuples():
        day=date.fromisoformat(str(r.first_day))
        if day.isoformat()!=str(r.first_day):raise ValueError("Invalid first day")
        zone=ZoneInfo(str(r.timezone))
        lo,hi=minute(r.available_from),minute(r.available_until)
        if hi-lo<210:raise ValueError("Availability must cover baseline delay plus final follow-up (210 min)")
        for i in range(21):
            day_i=day+timedelta(days=i)
            end=local_instant(day_i,hi,zone)
            candidates=[]
            for m in range(lo,hi-210+1):
                try:
                    start=local_instant(day_i,m,zone)
                except ValueError:continue
                if end.astimezone(UTC)-start.astimezone(UTC)>=timedelta(minutes=210):
                    candidates.append(start)
            if not candidates:raise ValueError("No valid prompt candidate on "+day_i.isoformat())
            token=hmac.new(key,(r.participant_id+"|"+day_i.isoformat()).encode(),hashlib.sha256).digest()
            # Deterministic independent per participant-day; negligible modulo bias.
            start=candidates[int.from_bytes(token,"big")%len(candidates)]
            wid=hashlib.sha256(("p07|"+r.participant_id+"|"+day_i.isoformat()).encode()).hexdigest()[:32]
            rows.append(dict(participant_id=r.participant_id,window_id=wid,study_day=i+1,
                             scheduled_time=start.isoformat(),local_day=day_i.isoformat(),timezone=str(r.timezone)))
    return pd.DataFrame(rows).sort_values(["participant_id","study_day"]).reset_index(drop=True)

def reconcile(schedule,responses):
    if not set(KEYS)<=set(schedule) or "window_id" not in responses:
        raise ValueError("Missing schedule or response keys")
    s=schedule.copy();r=responses.copy()
    for d in [s,r]:
        if d.window_id.isna().any() or d.window_id.astype(str).str.strip().eq("").any():raise ValueError("Invalid window ID")
        d["window_id"]=d.window_id.astype(str)
        if d.window_id.duplicated().any():raise ValueError("Duplicate window ID")
    if s.participant_id.isna().any() or s.participant_id.astype(str).str.strip().eq("").any():raise ValueError("Invalid schedule participant")
    s["participant_id"]=s.participant_id.astype(str)
    for _,g in s.groupby("participant_id"):
        if g.timezone.nunique(dropna=False)!=1:
            raise ValueError("Schedule timezone must stay fixed during study")
        try: zone=ZoneInfo(str(g.timezone.iloc[0]))
        except (ValueError,KeyError) as exc: raise ValueError("Invalid schedule timezone") from exc
        for row in g.itertuples():
            stamp=datetime.fromisoformat(str(row.scheduled_time).replace("Z","+00:00"))
            if stamp.utcoffset() is None or stamp.astimezone(zone).date().isoformat()!=str(row.local_day):
                raise ValueError("Scheduled instant contradicts local calendar")
            if stamp.utcoffset()!=stamp.astimezone(zone).utcoffset():
                raise ValueError("Frozen scheduled offset contradicts timezone")
        if sorted(pd.to_numeric(g.study_day,errors="raise").tolist())!=list(range(1,22)):
            raise ValueError("Schedule must have exactly 21 unique days per participant")
    if not set(r.window_id)<=set(s.window_id):raise ValueError("Unscheduled response")
    idx=s.set_index("window_id")
    for col in KEYS:
        if col=="window_id" or col not in r:continue
        expected=r.window_id.map(idx[col])
        if col=="scheduled_time":
            def instant(value):
                stamp=datetime.fromisoformat(str(value).replace("Z","+00:00"))
                if stamp.utcoffset() is None: raise ValueError("Timestamp offset required")
                return stamp.astimezone(UTC)
            same=r[col].map(instant).eq(expected.map(instant))
        elif col=="study_day":same=pd.to_numeric(r[col],errors="raise").eq(pd.to_numeric(expected))
        else:same=r[col].astype(str).eq(expected.astype(str))
        if not same.all():raise ValueError("Response contradicts frozen "+col)
    out=s.merge(r[["window_id"]+[c for c in RESPONSE if c in r]],on="window_id",how="left",validate="one_to_one",indicator=True)
    out["response_record_received"]=out.pop("_merge").eq("both")
    for col in RESPONSE:
        if col not in out:out[col]=np.nan
    return out

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("enrollment");p.add_argument("output")
    p.add_argument("--seed",required=True);a=p.parse_args()
    generate(pd.read_csv(a.enrollment,dtype=str),a.seed).to_csv(a.output,index=False)
