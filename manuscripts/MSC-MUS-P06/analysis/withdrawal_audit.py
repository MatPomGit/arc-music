"""Candidate pre-estimation audit for an institution-authorized P06 export.

No deletion or retention decision is made here. Exact cutoff is the first
instant with no further collection; the first fully inactive local day is
a separate calendar field. A failed gate returns no model.
"""
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
import pandas as pd
from ledger import TIMES, parse_time
from daily import dates, daily_ledger


def audit(enrollment,checkins,sessions):
    if enrollment is None or checkins is None:
        raise ValueError("Empirical analysis requires enrollment and check-in ledgers")
    if not {"participant_id","first_day","withdrawal_day","withdrawal_time","timezone"}<=set(enrollment):
        raise ValueError("Missing authoritative enrollment time/cutoff fields")
    if not {"participant_id","local_day","reported_sessions","checkin_time"}<=set(checkins):
        raise ValueError("Missing authoritative check-in time fields")
    if enrollment.empty:
        raise ValueError("Empty enrollment")
    e=enrollment.copy()
    if e.participant_id.isna().any() or e.participant_id.astype(str).str.strip().eq("").any():
        raise ValueError("Invalid enrollment identifier")
    e["participant_id"]=e.participant_id.astype(str)
    if e.participant_id.duplicated().any():raise ValueError("Duplicate enrollment")
    info={}
    for row in e.itertuples():
        first=dates(pd.Series([row.first_day])).iloc[0]
        try: zone=ZoneInfo(str(row.timezone))
        except (ValueError,KeyError) as exc:raise ValueError("Invalid enrollment timezone") from exc
        cutoff=parse_time(row.withdrawal_time)
        day=None if pd.isna(row.withdrawal_day) else dates(pd.Series([row.withdrawal_day])).iloc[0]
        if pd.isna(cutoff):
            if day is not None:raise ValueError("Withdrawal day requires exact cutoff")
        else:
            local=cutoff.tz_convert(zone)
            full_day=local.date()+(timedelta(days=1) if local.time()!=time(0) else timedelta())
            if day!=full_day or local.date()<first:
                raise ValueError("Withdrawal calendar contradicts exact cutoff")
        info[row.participant_id]=(zone,cutoff,first)
    def person(value):
        if pd.isna(value) or str(value) not in info:
            raise ValueError("Unknown participant in export")
        return info[str(value)]
    def check(stamp,cutoff):
        if pd.notna(stamp) and pd.notna(cutoff) and stamp>=cutoff:
            raise ValueError("Timestamp at or after withdrawal cutoff")
    for row in sessions.itertuples():
        zone,cutoff,first=person(row.participant_id)
        stamps={k:parse_time(getattr(row,k)) for k in TIMES}
        if all(pd.isna(v) for v in stamps.values()):
            raise ValueError("Session has no auditable event timestamp")
        for value in stamps.values():check(value,cutoff)
        for event,fields in (("pre_time",("avoidance","distress_pre","expected_difficulty")),
                             ("post_time",("distress_post","brooding","reflection")),
                             ("followup_time",("interference","activity_relevant","activity_completed","distress_followup","followup_activity_id"))):
            if pd.isna(stamps[event]) and any(pd.notna(getattr(row,k,None)) for k in fields):
                raise ValueError("Response payload lacks event timestamp")
        if pd.notna(stamps["start_time"]) and stamps["start_time"].tz_convert(zone).date().isoformat()!=str(row.local_day):
            raise ValueError("Session local day contradicts enrollment timezone")
    for row in checkins.itertuples():
        zone,cutoff,first=person(row.participant_id)
        stamp=parse_time(row.checkin_time)
        if pd.isna(stamp):raise ValueError("Check-in lacks timestamp")
        check(stamp,cutoff)
        if stamp.tz_convert(zone).date().isoformat()!=str(row.local_day):
            raise ValueError("Check-in day contradicts timestamp")
    return {"enrolled_participants":len(info),"session_records_checked":len(sessions),
            "checkin_records_checked":len(checkins),"timestamp_gate_passed":True,
            "policy_approved_by_code":False}
