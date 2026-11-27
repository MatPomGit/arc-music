"""P08 factorial assignment contrasts, complete outcome analysis."""
import argparse,json
import numpy as np
import pandas as pd
from scipy.stats import t
BASE=["training","prior_use_days","familiarity","anticipated_ownership"]
ITEMS={k:[k+str(j) for j in range(1,4)] for k in ["ownership","agency"]}
def prepare(frame):
    d=frame.copy()
    required={"participant_id","authority","manual","heard_version",*BASE,*ITEMS["ownership"],*ITEMS["agency"]}
    if not required<=set(d):raise ValueError("Missing columns")
    if d.participant_id.isna().any() or d.participant_id.astype(str).str.strip().eq("").any() or d.participant_id.astype(str).duplicated().any():raise ValueError("Invalid participant identifiers")
    for c in ["authority","manual",*BASE,*ITEMS["ownership"],*ITEMS["agency"]]:
        v=pd.to_numeric(d[c],errors="raise")
        hi=1 if c in ["authority","manual","training"] else 30 if c=="prior_use_days" else 10
        if not (v.dropna().between(0,hi)&(v.dropna()%1==0)).all():raise ValueError("Invalid score: "+c)
        if c in ["authority","manual",*BASE] and v.isna().any():raise ValueError("Missing randomisation or baseline value")
        d[c]=v
    if not d.heard_version.dropna().map(lambda x:isinstance(x,(bool,np.bool_))).all():raise ValueError("Invalid heard flag")
    for name,cols in ITEMS.items():
        d[name]=d[cols].mean(axis=1,skipna=False).where(d.heard_version.eq(True))
    return d

def design(d):
    a=d.authority.to_numpy(float)-.5;e=d.manual.to_numpy(float)-.5
    b=d[BASE].to_numpy(float)
    return np.column_stack([np.ones(len(d)),a,e,a*e,b-b.mean(axis=0)])

def fit(d,outcome):
    a=d.loc[d[outcome].notna()]
    if a.groupby(["authority","manual"]).ngroups!=4:raise ValueError("Missing factorial cell")
    return fit_arrays(design(a),a[outcome].to_numpy(float))

def fit_arrays(x,y):
    x=np.asarray(x,float);y=np.asarray(y,float)
    if x.ndim!=2 or x.shape[1]!=8 or y.ndim!=1 or len(x)!=len(y) or not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError("Invalid design or outcome")
    if not np.isin(x[:,1:3],[-.5,.5]).all() or len(np.unique(x[:,1:3],axis=0))!=4:raise ValueError("Missing or invalid factorial cell")
    if not np.allclose(x[:,0],1) or not np.allclose(x[:,3],x[:,1]*x[:,2]):raise ValueError("Invalid effect coding")
    n,p=x.shape
    if n<=p or np.linalg.matrix_rank(x)<p:raise ValueError("Insufficient or rank deficient design")
    bread=np.linalg.inv(x.T@x);b=bread@x.T@y
    h=np.sum((x@bread)*x,axis=1)
    if (h>=1-1e-10).any():raise ValueError("Degenerate leverage")
    scores=x*((y-x@b)/(1-h))[:,None]
    v=bread@(scores.T@scores)@bread
    result={}
    for k,j in [("authority",1),("execution",2),("interaction",3)]:
        se=float(np.sqrt(max(v[j,j],0)))
        if se<=0:raise ValueError("Degenerate uncertainty")
        q=t.ppf(.975,n-p)
        result[k]=dict(beta=float(b[j]),se=se,ci=[float(b[j]-q*se),float(b[j]+q*se)],p=float(2*t.sf(abs(b[j]/se),n-p)))
    return result

def holm(p):
    ordered=sorted(p,key=lambda k:1 if p[k] is None else p[k])
    out={};prev=0
    for i,k in enumerate(ordered):
        if p[k] is None:out[k]=None;continue
        prev=max(prev,min(1,(len(ordered)-i)*p[k]));out[k]=prev
    return out

def analyze(frame, bootstrap_draws=0, bootstrap_seed=2808):
    d=prepare(frame);models={};cells={}
    for a in [0,1]:
        for e in [0,1]:
            x=d[(d.authority==a)&(d.manual==e)]
            cells[f"{a}/{e}"]=dict(randomised=len(x),heard=int(x.heard_version.eq(True).sum()),
              unheard=int(x.heard_version.eq(False).sum()),hearing_unknown=int(x.heard_version.isna().sum()),
              ownership_observed=int(x.ownership.notna().sum()),agency_observed=int(x.agency.notna().sum()),
              ownership_mean=float(x.ownership.mean()) if x.ownership.notna().any() else None,
              agency_mean=float(x.agency.mean()) if x.agency.notna().any() else None)
    for k in ITEMS:
        try:models[k]=fit(d,k)
        except (ValueError,np.linalg.LinAlgError) as exc:models[k]={"unavailable":str(exc)}
    # Exposure defines both outcome constructs; do not treat selection into
    # the heard population as a causal full-cohort contrast.
    all_defined=bool(d.heard_version.eq(True).fillna(False).all())
    for k in ITEMS:
        if "unavailable" in models[k]:
            continue
        for result in models[k].values():
            result["confirmatory_available"]=all_defined
            if not all_defined:
                result["descriptive_p"]=result.pop("p")
                result["interpretation"]="Observed heard population only; no full-cohort causal contrast"
    h1=models["ownership"].get("authority");h2=models["agency"].get("authority");h3=models["ownership"].get("interaction")
    from sensitivity import assess, bootstrap
    sensitivity={}
    for key in ITEMS:
        try:
            sensitivity[key] = assess(d, key)
            if bootstrap_draws:
                sensitivity[key]["heard_only_bootstrap"] = bootstrap(
                    d, key, bootstrap_draws, bootstrap_seed
                )
        except (ValueError,np.linalg.LinAlgError) as exc:sensitivity[key]={"unavailable":str(exc)}
    return dict(randomised=len(d),cells=cells,models=models,hypotheses={"H1":h1,"H2":h2,"H3":h3},missingness=sensitivity,
                full_cohort_target_defined=all_defined,
                secondary_holm=holm({"H2":h2.get("p") if h2 else None,"H3":h3.get("p") if h3 else None}))
if __name__=="__main__":
    p = argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--data-kind",choices=["synthetic","empirical"],required=True)
    p.add_argument("--ledger")
    p.add_argument("--bootstrap-draws", type=int, default=0)
    p.add_argument("--bootstrap-seed", type=int, default=2808)
    a = p.parse_args()
    if a.bootstrap_draws != 0 and a.bootstrap_draws < 199:
        p.error("--bootstrap-draws must be zero or at least 199")
    frame=pd.read_csv(a.csv,dtype={"participant_id":str,"system_schedule":str})
    if a.data_kind=="empirical":
        if not a.ledger:p.error("Empirical mode requires authoritative ledger")
        from assignment_ledger import reconcile
        reconcile(a.ledger,frame)
    result=analyze(frame,a.bootstrap_draws,a.bootstrap_seed)
    result.update(data_kind=a.data_kind,confirmatory_authorized=False)
    print(json.dumps(result,indent=2,allow_nan=False))
