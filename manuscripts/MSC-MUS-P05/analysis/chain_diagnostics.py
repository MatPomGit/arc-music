"""Rank-normalized split R-hat and approximate bulk ESS for scalar traces.

These diagnostics apply to the retained sequence of imputed item means,
not to the joint FCS posterior. They cannot establish compatibility.
"""
import numpy as np
from scipy.stats import rankdata,norm

def _rank(x):
    r=rankdata(x.ravel(),method="average").reshape(x.shape)
    return norm.ppf((r-.375)/(x.size+.25))

def _rhat(x):
    n=x.shape[1]
    w=np.var(x,axis=1,ddof=1).mean()
    b=n*np.var(x.mean(axis=1),ddof=1)
    if w<=0:
        return None
    return float(np.sqrt(((n-1)*w/n+b/n)/w))

def _ess(x):
    m,n=x.shape
    w=np.var(x,axis=1,ddof=1).mean()
    b=n*np.var(x.mean(axis=1),ddof=1)
    v=(n-1)*w/n+b/n
    if v<=0:
        return None
    centered=x-x.mean(axis=1,keepdims=True)
    acov=np.stack([np.correlate(row,row,mode="full")[n-1:]/n for row in centered])
    rho=np.r_[1.,1-(w-acov.mean(axis=0)[1:])/v]
    pairs=[]
    for j in range(0,n-1,2):
        pair=float(rho[j]+rho[j+1])
        if pair<=0:
            break
        pairs.append(min(pair,pairs[-1]) if pairs else pair)
    tau=max(-1+2*sum(pairs),1.)
    return float(min(m*n,m*n/tau))

def diagnose(chains):
    """Require four independent chains and at least 20 retained sweeps."""
    x=np.asarray(chains,float)
    if x.ndim!=2 or x.shape[0]<4 or x.shape[1]<20 or not np.isfinite(x).all():
        return {"status":"insufficient_or_invalid_trace","rhat":None,"bulk_ess":None}
    n=x.shape[1]//2
    x=np.concatenate([x[:,:n],x[:,-n:]],axis=0)
    if np.ptp(x)==0:
        return {"status":"constant_trace","rhat":None,"bulk_ess":None}
    rank=_rank(x)
    r1=_rhat(rank); r2=_rhat(_rank(abs(x-np.median(x))))
    ess=_ess(rank)
    if r1 is None or r2 is None or ess is None:
        return {"status":"degenerate_trace","rhat":None,"bulk_ess":None}
    rh=max(1.,r1,r2)
    return {"status":"screen_pass" if rh<=1.01 and ess>=400 else "screen_flag",
            "rhat":rh,"bulk_ess":ess,"split_chains":len(x),"draws_per_split":n}

def summarize(diagnostics):
    if not diagnostics:
        raise ValueError("no chain diagnostics")
    items=diagnostics[0].get("item_mean_traces",{})
    out={}
    for key in items:
        out[key]=diagnose([d["item_mean_traces"][key] for d in diagnostics])
    return {"items":out,"all_screen_pass":bool(out) and all(v["status"]=="screen_pass" for v in out.values()),
            "interpretation":"imputed item mean screening only; not joint posterior convergence"}
