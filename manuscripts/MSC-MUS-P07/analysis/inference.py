"""Initial P07 H1 implementation; no causal claims."""
import argparse,json
from datetime import datetime
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

def prepare(frame):
    required={"participant_id","window_id","study_day",*TIMES,"creation_ongoing","creation_first_hour","valence0","arousal0","intention0","valence60"}
    if not required<=set(frame):raise ValueError("Missing columns")
    d=frame.copy()
    for c in ["participant_id","window_id"]:
        if d[c].isna().any() or d[c].astype(str).str.strip().eq("").any():raise ValueError("Missing identifier")
        d[c]=d[c].astype(str)
    if d.window_id.duplicated().any():raise ValueError("Duplicate window")
    for c in ["study_day","valence0","arousal0","intention0","valence60"]:
        v=pd.to_numeric(d[c],errors="raise"); lo,hi=(1,21) if c=="study_day" else (0,10)
        if not (v.dropna().between(lo,hi)&(v.dropna()%1==0)).all():raise ValueError("Invalid score")
        d[c]=v
    if d.study_day.isna().any() or d.duplicated(["participant_id","study_day"]).any():raise ValueError("Invalid study day schedule")
    for c in ["creation_ongoing","creation_first_hour"]:
        if not d[c].dropna().map(lambda v:isinstance(v,(bool,np.bool_))).all():raise ValueError("Invalid boolean")
    parsed={c:d[c].map(parse) for c in TIMES}
    d["local_hour"]=parsed["baseline_time"].map(lambda v: v.hour+v.minute/60+v.second/3600 if pd.notna(v) else np.nan)
    for c in TIMES:d[c]=pd.to_datetime(parsed[c],utc=True)
    if d.scheduled_time.isna().any():raise ValueError("Missing schedule")
    delay=lambda c:(d[c]-d.baseline_time).dt.total_seconds()/60
    base=(d.baseline_time-d.scheduled_time).dt.total_seconds()/60
    valid_base=base.between(0,15)&d.creation_ongoing.eq(False)&d[["valence0","arousal0","intention0"]].notna().all(axis=1)
    valid_exposure=delay("exposure_time").between(60,75)&d.creation_first_hour.notna()
    valid_outcome=delay("followup60_time").between(60,75)&d.valence60.notna()
    d["status"]=np.select([~valid_base,~valid_exposure,~valid_outcome],["baseline_unavailable_or_ongoing","exposure_unavailable","outcome_unavailable"],default="complete")
    a=d[d.status.eq("complete")].copy()
    a["creation_first_hour"]=a.creation_first_hour.astype(int)
    return d,a

def fit(a):
    switches=a.groupby("participant_id").creation_first_hour.nunique()
    a=a[a.participant_id.isin(switches[switches==2].index)]
    g=a.participant_id.to_numpy()
    x=a[PRED].to_numpy(float);y=a.valence60.to_numpy(float)
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

def analyze(frame):
    d,a=prepare(frame)
    return dict(scheduled=len(d),participants=int(d.participant_id.nunique()),status={k:int(v) for k,v in d.status.value_counts().items()},primary=fit(a))

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("csv");a=p.parse_args()
    print(json.dumps(analyze(pd.read_csv(a.csv,dtype={"participant_id":str,"window_id":str})),indent=2,allow_nan=False))
