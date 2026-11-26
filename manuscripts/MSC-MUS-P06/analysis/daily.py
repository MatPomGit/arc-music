"""Participant-day denominators, distinct from the session-level estimand."""
from datetime import date,timedelta
import numpy as np
import pandas as pd

def dates(series):
    def one(v):
        if pd.isna(v): raise ValueError("Missing calendar date")
        s=str(v)
        d=date.fromisoformat(s)
        if d.isoformat()!=s: raise ValueError("Use ISO calendar dates")
        return d
    return series.map(one)

def daily_ledger(enrollment,checkins,sessions):
    required={"participant_id","first_day","withdrawal_day"}
    if not required<=set(enrollment): raise ValueError("Missing enrollment columns")
    required={"participant_id","local_day","reported_sessions"}
    if not required<=set(checkins): raise ValueError("Missing daily check-in columns")
    e=enrollment.copy(); c=checkins.copy(); s=sessions.copy()
    for d in [e,c,s]:
        if d.participant_id.isna().any() or d.participant_id.astype(str).str.strip().eq("").any():
            raise ValueError("Invalid participant ID")
        d["participant_id"]=d.participant_id.astype(str)
    if e.participant_id.duplicated().any(): raise ValueError("Duplicate enrollment")
    e["first_day"]=dates(e.first_day)
    e["withdrawal_day"]=e.withdrawal_day.map(lambda v: None if pd.isna(v) else dates(pd.Series([v])).iloc[0])
    rows=[]
    for r in e.itertuples():
        if r.withdrawal_day is not None and r.withdrawal_day<r.first_day:
            raise ValueError("Withdrawal precedes enrollment")
        for day in range(1,15):
            local=r.first_day+timedelta(days=day-1)
            rows.append((r.participant_id,local,day,r.withdrawal_day is not None and local>=r.withdrawal_day))
    d=pd.DataFrame(rows,columns=["participant_id","local_day","study_day","withdrawn"])
    for f in [c,s]:
        f["local_day"]=dates(f.local_day)
        if len(f.merge(d[["participant_id","local_day"]],on=["participant_id","local_day"],how="left",indicator=True).query("_merge != 'both'")):
            raise ValueError("Record outside enrolled study days")
    if c.duplicated(["participant_id","local_day"]).any(): raise ValueError("Duplicate daily check-in")
    if "study_day" in s:
        aligned=s.merge(d[["participant_id","local_day","study_day"]],on=["participant_id","local_day"],suffixes=("","_expected"))
        if not pd.to_numeric(aligned.study_day,errors="raise").eq(aligned.study_day_expected).all():
            raise ValueError("Session study day contradicts enrollment")
    count=pd.to_numeric(c.reported_sessions,errors="raise")
    if not (count.dropna().ge(0)&(count.dropna()%1==0)).all(): raise ValueError("Invalid reported session count")
    c["reported_sessions"]=count
    c["checkin_received"]=True
    # Count started sessions, not drafts of pre-session forms.
    starts=s.loc[s.start_time.notna()].groupby(["participant_id","local_day"]).size().rename("logged_starts").reset_index()
    d=d.merge(c[["participant_id","local_day","reported_sessions","checkin_received"]],how="left",on=["participant_id","local_day"])
    d=d.merge(starts,how="left",on=["participant_id","local_day"])
    d["logged_starts"]=d.logged_starts.fillna(0).astype(int)
    d["checkin_received"]=d.checkin_received.eq(True)
    if (d.withdrawn & (d.checkin_received | d.logged_starts.gt(0))).any():
        raise ValueError("Data after effective withdrawal day")
    reported=d.reported_sessions
    d["day_status"]=np.select(
        [d.withdrawn,reported.notna() & reported.lt(d.logged_starts),
         reported.eq(0),reported.gt(d.logged_starts),reported.gt(0),
         d.logged_starts.gt(0),d.checkin_received],
        ["withdrawn","count_conflict","confirmed_no_creation","reported_unlogged_sessions",
         "reported_and_logged","logged_without_count","checkin_count_missing"],
        default="unknown_no_checkin")
    # Positive discrepancy is a lower bound, never fabricate unlogged outcomes.
    d["unlogged_lower_bound"]=(reported-d.logged_starts).clip(lower=0)
    return d

def summarize(d):
    active=d.loc[~d.withdrawn]
    return {"enrolled_participants":int(d.participant_id.nunique()),
            "scheduled_days":len(d),"active_days":len(active),
            "withdrawn_days":int(d.withdrawn.sum()),
            "received_checkins":int(active.checkin_received.sum()),
            "checkin_rate":float(active.checkin_received.mean()) if len(active) else None,
            "day_status":{str(k):int(v) for k,v in d.day_status.value_counts().items()},
            "reported_unlogged_lower_bound":int(active.unlogged_lower_bound.sum()),
            "count_conflicts":int(active.day_status.eq("count_conflict").sum())}
