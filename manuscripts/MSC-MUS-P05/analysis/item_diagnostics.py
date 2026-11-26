"""Ordinal item diagnostics for development; flags are not deletion rules."""
import numpy as np
from scipy.stats import spearmanr
from ordinal_efa import polychoric_matrix

def diagnose(x,domains,item_ids,loading=None,phi=None):
    x=np.asarray(x,float); d=np.asarray(domains)
    if x.ndim!=2 or len(x)<30 or d.shape!=(x.shape[1],) or len(item_ids)!=x.shape[1] or len(set(item_ids))!=len(item_ids):
        raise ValueError("invalid design")
    if np.isinf(x).any() or not np.isin(x[np.isfinite(x)],np.arange(5)).all():
        raise ValueError("invalid ordinal responses")
    for group in np.unique(d):
        if np.sum(d==group)<3:
            raise ValueError("at least three items per domain")
    items=[]
    for i,key in enumerate(item_ids):
        observed=x[np.isfinite(x[:,i]),i].astype(int)
        counts=np.bincount(observed,minlength=5)
        freq=counts/len(observed) if len(observed) else np.zeros(5)
        peers=x[:,(d==d[i]) & (np.arange(len(d))!=i)]
        keep=np.isfinite(x[:,i]) & np.isfinite(peers).all(axis=1)
        a=x[keep,i]; b=peers[keep].mean(axis=1)
        rho=float(spearmanr(a,b).statistic) if len(a)>=30 and np.ptp(a)>0 and np.ptp(b)>0 else None
        flags=[]
        if np.min(counts)<5: flags.append("sparse_category")
        if freq[0]>=.8 or freq[-1]>=.8: flags.append("extreme_endorsement")
        if len(observed)/len(x)<.9: flags.append("missingness")
        if rho is not None and rho<.30: flags.append("weak_item_rest")
        items.append({"id":key,"domain":str(d[i]),"observed":len(observed),"missing_fraction":1-len(observed)/len(x),
                      "counts":counts.tolist(),"frequencies":freq.tolist(),"item_rest_spearman":rho,
                      "item_rest_n":int(keep.sum()),"flags":flags})
    local=[]
    if (loading is None)!=(phi is None):
        raise ValueError("both loading and phi required")
    if loading is not None:
        l=np.asarray(loading,float); f=np.asarray(phi,float)
        if l.shape!=(len(d),) or f.shape!=(len(np.unique(d)),)*2 or not np.array_equal(np.unique(d),np.arange(len(f))):
            raise ValueError("invalid CFA dimensions or domain labels")
        if not np.isfinite(l).all() or np.any(abs(l)>=1) or not np.isfinite(f).all() or not np.allclose(f,f.T) or not np.allclose(np.diag(f),1) or np.linalg.eigvalsh(f)[0]<=0:
            raise ValueError("invalid CFA solution")
        complete=x[np.isfinite(x).all(axis=1)]
        obs=polychoric_matrix(complete)
        pred=l[:,None]*l[None,:]*f[d[:,None],d[None,:]]
        for i,j in zip(*np.tril_indices(len(d),-1)):
            residual=float(obs[i,j]-pred[i,j])
            if abs(residual)>=.15:
                local.append({"items":[item_ids[j],item_ids[i]],"residual":residual})
        local.sort(key=lambda v:-abs(v["residual"]))
    return {"label":"development flags; no automatic deletion", "n":len(x),"items":items,
            "local_dependence_flags":local,"local_dependence_available":loading is not None,
            "complete_n":int(np.isfinite(x).all(axis=1).sum())}
