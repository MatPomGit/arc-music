"""P07 outcome-specific complete-window switcher models; no causal claims."""
import argparse,json
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from scipy.stats import t
PRED=["creation_first_hour","valence0","arousal0","intention0","study_day","local_hour"]
TIMES=["scheduled_time","baseline_time","exposure_time","followup60_time"]

def parse(v):
    if pd.isna(v):return None
    d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
    if d.utcoffset() is None:raise ValueError("Timezone offset required")
    return d

def prepare(frame, upper_delay=15):
    if upper_delay not in (5,15): raise ValueError("Invalid prespecified timing tolerance")
    required={"participant_id","window_id","study_day",*TIMES,"creation_ongoing","creation_first_hour","valence0","arousal0","intention0","valence60"}
    if not required<=set(frame):raise ValueError("Missing columns")
    d=frame.copy()
    for c in ["participant_id","window_id"]:
        if d[c].isna().any() or d[c].astype(str).str.strip().eq("").any():raise ValueError("Missing identifier")
        d[c]=d[c].astype(str)
    if d.window_id.duplicated().any():raise ValueError("Duplicate window")
    for c in ["desired_arousal0","arousal60","valence180","arousal180","followup180_time"]:
        if c not in d: d[c]=np.nan
    for c in ["study_day","valence0","arousal0","intention0","valence60","desired_arousal0","arousal60","valence180","arousal180"]:
        v=pd.to_numeric(d[c],errors="raise"); lo,hi=(1,21) if c=="study_day" else (0,10)
        if not (v.dropna().between(lo,hi)&(v.dropna()%1==0)).all():raise ValueError("Invalid score")
        d[c]=v
    if d.study_day.isna().any() or d.duplicated(["participant_id","study_day"]).any():raise ValueError("Invalid study day schedule")
    for c in ["creation_ongoing","creation_first_hour"]:
        if not d[c].dropna().map(lambda v:isinstance(v,(bool,np.bool_))).all():raise ValueError("Invalid boolean")
    parsed={c:d[c].map(parse) for c in TIMES+["followup180_time"]}
    # Response offsets represent instants, not the study timezone.
    zones=[]
    for i,stamp in enumerate(parsed["scheduled_time"]):
        if pd.isna(stamp):
            raise ValueError("Missing schedule")
        if "timezone" in d:
            try: zone=ZoneInfo(str(d["timezone"].iloc[i]))
            except (ValueError,KeyError) as exc: raise ValueError("Invalid schedule timezone") from exc
        else:
            zone=stamp.tzinfo  # direct synthetic fixtures only
        zones.append(zone)
    def hour(value,zone):
        if pd.isna(value):return np.nan
        v=value.astimezone(zone)
        return v.hour+v.minute/60+v.second/3600+v.microsecond/3.6e9
    d["local_hour"]=[hour(v,z) for v,z in zip(parsed["baseline_time"],zones)]
    for c in TIMES+["followup180_time"]:d[c]=pd.to_datetime(parsed[c],utc=True)
    if d.scheduled_time.isna().any():raise ValueError("Missing schedule")
    delay=lambda c:(d[c]-d.baseline_time).dt.total_seconds()/60
    base=(d.baseline_time-d.scheduled_time).dt.total_seconds()/60
    valid_base=base.between(0,upper_delay)&d.creation_ongoing.eq(False)&d[["valence0","arousal0","intention0"]].notna().all(axis=1)
    valid_exposure=delay("exposure_time").between(60,60+upper_delay)&d.creation_first_hour.notna()
    valid_outcome=delay("followup60_time").between(60,60+upper_delay)&d.valence60.notna()
    cancelled=d["withdrawn_before_prompt"].astype(bool) if "withdrawn_before_prompt" in d else pd.Series(False,index=d.index)
    valid_base=valid_base & ~cancelled
    d["status"]=np.select([cancelled,base.between(0,upper_delay)&d.creation_ongoing.eq(True),~valid_base,~valid_exposure,~valid_outcome],["cancelled_after_withdrawal","ongoing_creation","baseline_unavailable","exposure_unavailable","outcome_unavailable"],default="complete")
    d["baseline_valid"]=valid_base
    d["exposure_valid"]=valid_exposure
    d["outcome60_valid"]=valid_outcome
    d["h1_valid"]=valid_base & valid_exposure & valid_outcome
    d["h2_valid"]=valid_base & valid_exposure & delay("followup180_time").between(180,180+upper_delay) & d.valence180.notna()
    d["deviation0"]=(d.arousal0-d.desired_arousal0).abs()
    d["deviation60"]=(d.arousal60-d.desired_arousal0).abs()
    d["h3_valid"]=valid_base & valid_exposure & delay("followup60_time").between(60,60+upper_delay) & d.deviation60.notna() & d.deviation0.notna()
    a=d[d.h1_valid].copy()
    a["creation_first_hour"]=a.creation_first_hour.astype(int)
    return d,a

def switcher_rows(a):
    switches=a.groupby("participant_id").creation_first_hour.nunique()
    return a[a.participant_id.isin(switches[switches==2].index)].copy()

def fit(a, outcome="valence60", predictors=None):
    predictors=PRED if predictors is None else predictors
    return fit_arrays(a.participant_id.to_numpy(),a[predictors].to_numpy(float),a[outcome].to_numpy(float))

def fit_arrays(group,x,y):
    group=np.asarray(group);x=np.asarray(x,float);y=np.asarray(y,float)
    if x.ndim!=2 or x.shape[1]<1 or y.ndim!=1 or group.ndim!=1 or not len(x)==len(y)==len(group):
        raise ValueError("Invalid input shape")
    if not np.isfinite(x).all() or not np.isfinite(y).all() or not np.isin(x[:,0],[0,1]).all():
        raise ValueError("Invalid model values")
    _,g=np.unique(group,return_inverse=True)
    total=np.bincount(g)
    exposed=np.bincount(g,weights=x[:,0])
    keep=(exposed[g]>0)&(exposed[g]<total[g])
    g,x,y=g[keep],x[keep],y[keep]
    _,g=np.unique(g,return_inverse=True); counts=np.bincount(g)
    G,N,p=len(counts),len(y),x.shape[1]
    if G<10 or N-G-p<=0:raise ValueError("Insufficient switcher clusters")
    xm=np.zeros((G,p));ym=np.zeros(G)
    np.add.at(xm,g,x);np.add.at(ym,g,y)
    x=x-xm[g]/counts[g,None];y=y-ym[g]/counts[g]
    if np.linalg.matrix_rank(x)<p:raise ValueError("Rank deficient design")
    bread=np.linalg.inv(x.T@x);b=bread@x.T@y
    scores=np.zeros((G,p));np.add.at(scores,g,x*(y-x@b)[:,None])
    v=bread@(scores.T@scores)@bread*(G/(G-1))*((N-1)/(N-G-p))
    se=float(np.sqrt(max(v[0,0],0)))
    if se<=0:raise ValueError("Degenerate uncertainty")
    critical=t.ppf(.975,G-1)
    return dict(switchers=G,windows=N,beta=float(b[0]),se=se,ci=[float(b[0]-critical*se),float(b[0]+critical*se)],p=float(2*t.sf(abs(b[0]/se),G-1)))

MODELS={"H1":("h1_valid","valence60",PRED),
        "H2":("h2_valid","valence180",PRED),
        "H3":("h3_valid","deviation60",PRED+["deviation0"])}

def safe_fit(a,outcome,predictors):
    b=switcher_rows(a)
    out={"complete_windows":len(a),"complete_participants":int(a.participant_id.nunique()),
         "switcher_windows":len(b),"switcher_participants":int(b.participant_id.nunique())}
    try:out["estimate"]=fit(b,outcome,predictors)
    except (ValueError,np.linalg.LinAlgError) as exc:out["unavailable"]=str(exc)
    return out

def holm(pvalues):
    # Keep the prespecified two-test family even when one test is unavailable.
    ordered=sorted(pvalues,key=lambda k: 1.0 if pvalues[k] is None else pvalues[k])
    adjusted={}; prev=0.
    for i,k in enumerate(ordered):
        if pvalues[k] is None:adjusted[k]=None;continue
        prev=max(prev,min(1.,(len(ordered)-i)*pvalues[k]))
        adjusted[k]=prev
    return adjusted

def exposure_flow(d, flag):
    """Mutually exclusive participant categories, including zero response."""
    ids=pd.Index(d.participant_id.unique())
    def categories(mask):
        a=d.loc[mask & d.exposure_valid]
        counts=a.groupby("participant_id").creation_first_hour.agg(
            n="size", exposed="sum").reindex(ids,fill_value=0)
        n=counts.n.to_numpy(int); k=counts.exposed.to_numpy(int)
        cat=np.select([n==0,k==0,k==n],
                      ["no_known_window","noncreation_only","creation_only"],
                      default="both")
        return {"participants":len(ids),"no_known_window":int((cat=="no_known_window").sum()),
                "noncreation_only":int((cat=="noncreation_only").sum()),
                "creation_only":int((cat=="creation_only").sum()),"both":int((cat=="both").sum()),
                "windows":int(n.sum()),"creation_windows":int(k.sum()),
                "noncreation_windows":int((n-k).sum())}
    return {"valid_baseline_known_exposure":categories(d.baseline_valid),
            "complete_for_endpoint":categories(d[flag]),
            "interpretation":"Observed exposure support only; absence of switching is not proof of structural nonpositivity."}


def model_set(d):
    models={}
    for key,(flag,outcome,predictors) in MODELS.items():
        a=d.loc[d[flag]].copy()
        a["creation_first_hour"]=a.creation_first_hour.astype(int)
        models[key]=safe_fit(a,outcome,predictors)
        models[key]["participant_flow"]=exposure_flow(d,flag)
    return models

def analyze(frame, sensitivity_draws=100, schedule=None, withdrawals=None):
    if withdrawals is not None and schedule is None:raise ValueError("Withdrawal log requires frozen schedule")
    if schedule is not None:
        from schedule import reconcile
        frame=reconcile(schedule,frame)
    if withdrawals is not None:
        from withdrawal import apply_withdrawal
        frame=apply_withdrawal(frame,withdrawals)
    d,a=prepare(frame)
    models=model_set(d)
    pvalues={key:models[key].get("estimate",{}).get("p") for key in ["H2","H3"]}
    common=d.loc[d.h1_valid & d.h2_valid & d.h3_valid].copy()
    common["creation_first_hour"]=common.creation_first_hour.astype(int)
    shared={key:safe_fit(common,outcome,predictors) for key,(_,outcome,predictors) in MODELS.items()}
    narrow,_=prepare(frame,upper_delay=5)
    result=dict(scheduled=len(d),participants=int(d.participant_id.nunique()),
                status={k:int(v) for k,v in d.status.value_counts().items()},
                baseline_valid=int(d.baseline_valid.sum()),
                exposure_valid_given_baseline=int((d.baseline_valid & d.exposure_valid).sum()),
                models=models,secondary_holm=holm(pvalues),common_subset=shared,
                timing_sensitivity={"baseline_minutes":[0,5],"followup60_minutes":[60,65],
                                    "followup180_minutes":[180,185],"models":model_set(narrow)})
    result["schedule_verified"]=schedule is not None
    if schedule is not None:
        result["response_records_received"]=int(frame.response_record_received.sum())
        result["scheduled_without_response_record"]=int((~frame.response_record_received).sum())
    if withdrawals is not None:
        from withdrawal import summarize
        result["withdrawal_flow"]=summarize(d)
    else:result["withdrawal_flow_unavailable"]="No verified cessation log supplied"
    if "estimate" in models["H1"]:result["primary"]=models["H1"]["estimate"]
    else:result["primary_unavailable"]=models["H1"]["unavailable"]
    from sensitivity import assess
    try: result["missingness"]=assess(d,draws=sensitivity_draws)
    except (ValueError,np.linalg.LinAlgError) as exc: result["missingness_unavailable"]=str(exc)
    from joint_sensitivity import assess_joint
    try: result["joint_missingness"]=assess_joint(d,draws=sensitivity_draws)
    except (ValueError,np.linalg.LinAlgError) as exc: result["joint_missingness_unavailable"]=str(exc)
    from extended_calibration import outcome_bounds
    result["secondary_outcome_bounds"]={}
    for key in ("H2","H3"):
        flag,outcome,predictors=MODELS[key]
        known=d.baseline_valid & d.exposure_valid
        if key=="H3":known=known & d.deviation0.notna()
        a=d.loc[known]
        upper=np.full(len(a),10.) if key=="H2" else np.maximum(a.desired_arousal0,10-a.desired_arousal0).to_numpy(float)
        try:
            lo,hi=outcome_bounds(a.participant_id.to_numpy(),a[predictors].to_numpy(float),a[outcome].to_numpy(float),a[flag].to_numpy(bool),upper)
            result["secondary_outcome_bounds"][key]={"lower":lo,"upper":hi,"known_exposure_windows":len(a),"interpretation":"Finite-window outcome bounds, not a confidence interval; excludes missing exposure and invalid baseline."}
        except (ValueError,np.linalg.LinAlgError) as exc:result["secondary_outcome_bounds"][key]={"unavailable":str(exc)}
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("csv");p.add_argument("--schedule",required=True);p.add_argument("--withdrawals",required=True);a=p.parse_args()
    d=pd.read_csv(a.csv,dtype={"participant_id":str,"window_id":str})
    s=pd.read_csv(a.schedule,dtype={"participant_id":str,"window_id":str})
    w=pd.read_csv(a.withdrawals,dtype={"participant_id":str})
    print(json.dumps(analyze(d,schedule=s,withdrawals=w),indent=2,allow_nan=False))
