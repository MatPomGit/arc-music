"""P09 prospective assignment contrasts; no participant data."""
import argparse,json
from datetime import datetime
import numpy as np
import pandas as pd
from scipy.stats import t
BASE=["importance0","training","prior_use_days"]
ITEMS={j:[f"understanding{j}{k}" for k in (1,2,3)] for j in (0,1,2)}
def parse(v):
    if pd.isna(v):return None
    d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
    if d.utcoffset() is None:raise ValueError("Timezone offset required")
    return d

def prepare(frame):
    d=frame.copy()
    scores=["music",*BASE,"distance0","distance1",*sum(ITEMS.values(),[])]
    times=["randomised_at","t1_at","t2_at"]
    if not {"participant_id","same_event1","same_event2","target_status1","target_status2",*times,*scores}<=set(d):raise ValueError("Missing columns")
    ids=d.participant_id.astype(str)
    if d.participant_id.isna().any() or ids.str.strip().eq("").any() or ids.duplicated().any():raise ValueError("Invalid participant ID")
    for c in scores:
        v=pd.to_numeric(d[c],errors="raise");hi=1 if c in ("music","training") else 30 if c=="prior_use_days" else 10
        if not (v.dropna().between(0,hi)&(v.dropna()%1==0)).all():raise ValueError("Invalid score "+c)
        if c in ["music",*BASE,"distance0",*ITEMS[0]] and v.isna().any():raise ValueError("Missing baseline or assignment")
        d[c]=v
    for c in times:d[c]=pd.to_datetime(d[c].map(parse),utc=True)
    if d.randomised_at.isna().any():raise ValueError("Missing assignment timestamp")
    for j in (1,2):
        c=f"same_event{j}"
        if not d[c].dropna().map(lambda v:isinstance(v,(bool,np.bool_))).all():raise ValueError("Invalid event flag")
        elapsed=(d[f"t{j}_at"]-d.randomised_at).dt.total_seconds()/3600
        lo,hi=(0,.5) if j==1 else (144,192)
        timely=elapsed.between(lo,hi);same=d[c].eq(True)
        d[f"valid{j}"]=timely&same
        d[f"timely{j}"]=timely
        d[f"event_confirmed{j}"]=same
    for j in (0,1,2):
        d[f"understanding{j}"]=d[ITEMS[j]].mean(axis=1,skipna=False)
        if j:d[f"understanding{j}"]=d[f"understanding{j}"].where(d[f"valid{j}"])
    d["distance1"]=d.distance1.where(d.valid1)
    for j in (1,2):
        c=f"target_status{j}"
        if not d[c].isin(("defined","undefined","unknown")).all():
            raise ValueError("Invalid target status "+c)
        observed=d[f"understanding{j}"].notna()
        if j==1:observed=observed|d.distance1.notna()
        if (observed & d[c].ne("defined")).any():
            raise ValueError("Observed valid score with undefined or unresolved target")
    return d

def design(d,baseline):
    x=d[[baseline,*BASE]].to_numpy(float)
    return np.column_stack([np.ones(len(d)),d.music.to_numpy(float),x-x.mean(axis=0)])

def fit_arrays(x,y):
    x=np.asarray(x,float);y=np.asarray(y,float)
    if x.ndim!=2 or x.shape[1]!=6 or len(x)!=len(y) or y.ndim!=1 or not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError("Invalid model values")
    n,p=x.shape
    if n<=p or np.linalg.matrix_rank(x)<p or not np.array_equal(np.unique(x[:,1]),[0.,1.]):raise ValueError("Insufficient or rank deficient design")
    bread=np.linalg.inv(x.T@x);b=bread@x.T@y
    h=np.sum((x@bread)*x,axis=1)
    if (h>=1-1e-10).any():raise ValueError("Degenerate leverage")
    s=x*((y-x@b)/(1-h))[:,None];v=bread@(s.T@s)@bread
    se=float(np.sqrt(max(v[1,1],0)))
    if se<=0:raise ValueError("Degenerate uncertainty")
    q=t.ppf(.975,n-p)
    return dict(n=n,beta=float(b[1]),se=se,ci=[float(b[1]-q*se),float(b[1]+q*se)],p=float(2*t.sf(abs(b[1]/se),n-p)))

def holm(p):
    ordered=sorted(p,key=lambda k:1 if p[k] is None else p[k]);out={};prev=0
    for i,k in enumerate(ordered):
        if p[k] is None:out[k]=None;continue
        prev=max(prev,min(1,(len(ordered)-i)*p[k]));out[k]=prev
    return out

MODELS={"H1":("understanding2","understanding0"),"H2":("understanding1","understanding0"),"H3":("distance1","distance0")}
def sensitivity(d,outcome,baseline):
    x=design(d,baseline);y=d[outcome].to_numpy(float);k=np.isfinite(y)
    intervals=[]
    for a in (0,1):
        v=y[d.music.to_numpy()==a]
        if not len(v):raise ValueError("Empty assigned arm")
        intervals.append((float(np.nansum(v)/len(v)),float((np.nansum(v)+10*np.isnan(v).sum())/len(v))))
    result={"unadjusted_hypothetical_bounds":[intervals[1][0]-intervals[0][1],intervals[1][1]-intervals[0][0]]}
    try:
        fit_arrays(x[k],y[k]);b=np.linalg.lstsq(x[k],y[k],rcond=None)[0];pred=x@b
        result["shift_scenarios"]={f"{a}/{b}":float(np.linalg.lstsq(x,np.where(k,y,np.clip(pred+np.where(x[:,1]==0,a,b),0,10)),rcond=None)[0][1]) for a in (-2,-1,0,1,2) for b in (-2,-1,0,1,2)}
    except (ValueError,np.linalg.LinAlgError) as exc:result["unavailable"]=str(exc)
    return result

def analyze(frame):
    d=prepare(frame);models={};sens={};flow={}
    for a in (0,1):
        g=d[d.music==a]
        flow[str(a)]={"randomised":len(g),"timely1":int(g.timely1.sum()),"timely2":int(g.timely2.sum()),"valid1":int(g.valid1.sum()),"valid2":int(g.valid2.sum()),"observed":{h:int(g[o].notna().sum()) for h,(o,_) in MODELS.items()}}
    for arm in (0,1):
        g=d[d.music==arm]
        visits={}
        for j in (1,2):
            timestamp=g[f"t{j}_at"]
            event=g[f"same_event{j}"]
            valid=g[f"valid{j}"]
            items=ITEMS[j]
            visits[str(j)]={
                "missing_timestamp":int(timestamp.isna().sum()),
                "outside_window":int((timestamp.notna() & ~g[f"timely{j}"]).sum()),
                "wrong_event":int(event.eq(False).sum()),
                "unknown_event":int(event.isna().sum()),
                "missing_items_at_valid_visit":{c:int((valid & g[c].isna()).sum()) for c in items},
                "incomplete_composite_at_valid_visit":int((valid & g[items].isna().any(axis=1)).sum()),
                "target_status":{k:int(g[f"target_status{j}"].eq(k).sum()) for k in ("defined","undefined","unknown")}
            }
            if j==1:
                visits[str(j)]["missing_distance_at_valid_visit"]=int((valid & g.distance1.isna()).sum())
        flow[str(arm)]["visit_diagnostics_nonexclusive"]=visits
    for h,(o,b) in MODELS.items():
        a=d[d[o].notna()]
        try:models[h]=fit_arrays(design(a,b),a[o].to_numpy(float))
        except (ValueError,np.linalg.LinAlgError) as exc:models[h]={"unavailable":str(exc)}
        status="target_status2" if h=="H1" else "target_status1"
        if not d[status].eq("defined").all():
            sens[h]={"unavailable":"Full-cohort outcome undefined or unresolved",
                     "target_status":d.groupby("music")[status].value_counts().unstack(fill_value=0).to_dict(orient="index")}
            models[h]["interpretation"]="Observed defined outcomes only; not full-cohort assignment contrast"
            # Do not advertise a confirmatory test of an undefined cohort contrast.
            if "p" in models[h]:
                models[h]["descriptive_p"]=models[h].pop("p")
            models[h]["confirmatory_available"]=False
        else:
            try:sens[h]=sensitivity(d,o,b)
            except (ValueError,np.linalg.LinAlgError) as exc:sens[h]={"unavailable":str(exc)}
    return dict(randomised=len(d),flow=flow,hypotheses=models,secondary_holm=holm({h:models[h].get("p") for h in ("H2","H3")}),missingness=sens)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("csv");a=p.parse_args()
    print(json.dumps(analyze(pd.read_csv(a.csv,dtype={"participant_id":str})),indent=2,allow_nan=False))
