"""Validated session ledger; retain missing outcomes and distinguish exclusions."""
from datetime import datetime
import numpy as np
import pandas as pd

PREDICTORS = ["avoidance","distress_pre","expected_difficulty","study_day"]
TIMES = ["pre_time","start_time","end_time","post_time","followup_time"]
FLAGS = ["eligible_first","activity_defined"]
OPTIONAL_SCORES = ["distress_post","brooding","reflection","distress_followup"]

def parse_time(value):
    if pd.isna(value):
        return pd.NaT
    x=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if x.utcoffset() is None:
        raise ValueError("Timezone offset required")
    return pd.Timestamp(x).tz_convert("UTC")

def ledger(frame, upper_hours=28):
    if upper_hours not in (26,28):
        raise ValueError("Only prespecified follow-up windows are allowed")
    required={"participant_id","session_id","local_day","activity_id","followup_activity_id","activity_relevant",*FLAGS,*TIMES,*PREDICTORS,"interference"}
    if not required<=set(frame):
        raise ValueError(f"Missing columns: {sorted(required-set(frame))}")
    d=frame.copy()
    for col in ["participant_id","session_id"]:
        if d[col].isna().any() or d[col].astype(str).str.strip().eq("").any():
            raise ValueError("Missing or blank identifier")
        d[col]=d[col].astype(str)
    if d.session_id.duplicated().any():
        raise ValueError("Duplicate session identifier")
    for flag in FLAGS:
        if not d[flag].map(lambda v:isinstance(v,(bool,np.bool_))).all():
            raise ValueError(f"Invalid flag: {flag}")
    # A unique opaque token per planned activity, never the description.
    for col in ["activity_id","followup_activity_id"]:
        d[col]=d[col].map(lambda v: None if pd.isna(v) or not str(v).strip() else str(v).strip())
    if (d.activity_defined & d.activity_id.isna()).any():
        raise ValueError("Defined activity requires identifier")
    if d.loc[d.activity_defined,"activity_id"].duplicated().any():
        raise ValueError("Activity identifier reused across sessions")
    if not d.activity_relevant.dropna().map(lambda v:isinstance(v,(bool,np.bool_))).all():
        raise ValueError("Invalid activity relevance flag")
    for col in PREDICTORS+["interference"]+[c for c in OPTIONAL_SCORES if c in d]:
        v=pd.to_numeric(d[col],errors="raise")
        lo,hi=(1,14) if col=="study_day" else (0,10)
        nonnull=v.dropna()
        if not (nonnull.between(lo,hi)&(nonnull%1==0)).all():
            raise ValueError(f"Invalid score: {col}")
        d[col]=v
    # Compare local day using the offset recorded at session start, not UTC.
    def local_date(value):
        if pd.isna(value): return None
        x=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        if x.utcoffset() is None: raise ValueError("Timezone offset required")
        return x.date().isoformat()
    local=d.start_time.map(local_date)
    if not d.local_day.astype(str).str.fullmatch(r"\d{4}-\d{2}-\d{2}").all():
        raise ValueError("Invalid local day")
    if (local.notna() & local.ne(d.local_day.astype(str))).any():
        raise ValueError("Start timestamp and local day disagree")
    for col in TIMES:
        d[col]=pd.to_datetime(d[col].map(parse_time),utc=True)
    # First eligible designation comes from the prospectively recorded flag.
    # Reject contradictions with earlier logged eligible starts.
    first=d[d.eligible_first]
    if first.duplicated(["participant_id","local_day"]).any():
        raise ValueError("More than one eligible session per day")
    candidates=d[d.activity_defined & d.start_time.notna()]
    earliest=candidates.groupby(["participant_id","local_day"]).start_time.min()
    for row in first.itertuples():
        key=(row.participant_id,row.local_day)
        if row.activity_defined and key in earliest.index and pd.notna(row.start_time) and row.start_time>earliest.loc[key]:
            raise ValueError("First eligible flag contradicts earlier logged start")
    delta=lambda end,start:(d[end]-d[start]).dt.total_seconds()/60
    pre=delta("start_time","pre_time")
    duration=delta("end_time","start_time")
    post=delta("post_time","end_time")
    follow=delta("followup_time","end_time")/60
    # Primary eligibility is determined without post-session response.
    # End event is required for a well-defined follow-up window.
    status=np.select([~d.eligible_first,~d.activity_defined,
                      d[PREDICTORS].isna().any(axis=1),
                      ~pre.between(0,15),~(duration>0)],
                     ["not_first","no_activity","missing_predictor",
                      "invalid_pre","invalid_session"],default="eligible")
    d["session_status"]=status
    d["post_valid"]=post.between(0,15)
    for c in OPTIONAL_SCORES[:3]:
        if c in d: d.loc[~d.post_valid,c]=np.nan
    same_activity=d.activity_id.notna() & d.followup_activity_id.notna() & d.activity_id.eq(d.followup_activity_id)
    relevant=d.activity_relevant.map(lambda v: bool(v) if pd.notna(v) else False)
    follow_status=np.select([d.followup_time.isna(),~follow.between(24,upper_hours),
                             ~same_activity,d.activity_relevant.isna(),~relevant,d.interference.isna()],
                            ["no_followup","outside_window","activity_mismatch","relevance_unknown","activity_no_longer_relevant","missing_score"],
                            default="observed")
    d["followup_status"]=follow_status
    d["interference_raw"]=d.interference
    d.loc[d.followup_status.ne("observed"),"interference"]=np.nan
    if "activity_completed" in d:
        d["activity_completed"]=d["activity_completed"].astype("boolean")
        d.loc[d.followup_status.ne("observed"),"activity_completed"]=pd.NA
    return d

def analysis_ledger(frame, upper_hours=28):
    d=ledger(frame, upper_hours=upper_hours)
    return d.loc[d.session_status.eq("eligible")].copy()

def flow_counts(d):
    eligible=d[d.session_status.eq("eligible")]
    return {"logged_sessions":len(d),
            "participants_logged":int(d.participant_id.nunique()),
            "session_status":{str(k):int(v) for k,v in d.session_status.value_counts().items()},
            "eligible_sessions":len(eligible),
            "eligible_participants":int(eligible.participant_id.nunique()),
            "valid_post":int(eligible.post_valid.sum()),
            "followup_status":{str(k):int(v) for k,v in eligible.followup_status.value_counts().items()}}
