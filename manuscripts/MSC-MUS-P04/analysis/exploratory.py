"""Exploratory moderator specificity and nonlinear moderation, prospective only."""
import numpy as np
from inference import (design, fit_hc3, contrast, impute_pmm,
                       pooled_contrast, target_weights)

def _scores(values, required=False):
    v=np.asarray(values,float)
    if v.ndim!=1 or np.isinf(v).any() or (required and np.isnan(v).any()):
        raise ValueError("Invalid PAQ scores")
    present=v[np.isfinite(v)]
    if np.any((present<4)|(present>28)|(present!=np.floor(present))):
        raise ValueError("Facet scores must be authorised integer sums 4 to 28")
    return v

def _fit(x,y,m,seed):
    b,v,df=fit_hc3(x,y)
    w=target_weights(x)
    return {"complete_outcome":contrast(b,v,df,w),
            "mar":pooled_contrast(x,impute_pmm(x,y,m,seed),w)}

def facet_sensitivity(arm, nddf, ndif, cov, outcome, m=50, seed=20261126, bootstrap=2000):
    a,d,f,c,y=map(lambda v:np.asarray(v,float),(arm,nddf,ndif,cov,outcome))
    d,f=_scores(d,True),_scores(f)
    if a.shape!=d.shape or f.shape!=d.shape or y.shape!=d.shape or c.shape!=(len(d),5):
        raise ValueError("Invalid dimensions")
    if bootstrap<2:
        raise ValueError("Too few bootstrap draws")
    valid=np.isfinite(f)
    a,d,f,c,y=a[valid],d[valid],f[valid],c[valid],y[valid]
    if len(d)<4 or min(d.std(),f.std())==0:
        raise ValueError("Non-estimable facet correlation")
    rng=np.random.default_rng(seed)
    correlation=float(np.corrcoef(d,f)[0,1])
    draws=[]
    for _ in range(bootstrap):
        ix=rng.integers(len(d),size=len(d))
        if min(d[ix].std(),f[ix].std())>0:
            draws.append(float(np.corrcoef(d[ix],f[ix])[0,1]))
    if len(draws)<.95*bootstrap:
        raise ValueError("Too many degenerate bootstrap samples")
    return {"status":"EXPLORATORY","n_common":len(d),
            "n_excluded_missing_ndif":int((~valid).sum()),
            "pearson_r":correlation,"pearson_percentile95":np.quantile(draws,[.025,.975]).tolist(),
            "bootstrap_valid":len(draws),
            "models":{name:_fit(design(a,s,c),y,m,seed)
                      for name,s in (("N_DDF_common",d),("N_DIF",f),("N_DAF",d+f))}}

def rcs(value,knots):
    """One nonlinear restricted cubic spline basis with three fixed knots."""
    lo,mid,hi=knots
    if not lo<mid<hi:
        raise ValueError("Non-distinct knots")
    t=np.asarray(value,float)
    pos=lambda k:np.maximum(t-k,0)**3
    return (pos(lo)-(hi-lo)/(hi-mid)*pos(mid)+(mid-lo)/(hi-mid)*pos(hi))/(hi-lo)**2

def spline_sensitivity(arm, nddf, cov, outcome, m=50, seed=20261126):
    a=np.asarray(arm,float); d=_scores(nddf,True)
    y=np.asarray(outcome,float); c=np.asarray(cov,float)
    x=design(a,d,c)
    z=x[:,2]
    knots=np.quantile(z,[.1,.5,.9])
    basis=rcs(z,knots)
    # Within-arm imputation includes the nonlinear main term; its interaction is implicit.
    xi=np.column_stack((x,basis))
    xm=np.column_stack((xi,x[:,1]*basis))
    draws=impute_pmm(xi,y,m,seed)
    w=np.zeros(xm.shape[1]); w[-1]=1
    nonlinear=pooled_contrast(xm,draws,w)
    lo=max(z[a==0].min(),z[a==1].min())
    hi=min(z[a==0].max(),z[a==1].max())
    contrasts={}
    for v in (-1.,0.,1.):
        if lo<=v<=hi:
            w=np.zeros(xm.shape[1]); w[1]=1; w[3]=v; w[-1]=rcs(v,knots)
            contrasts[str(v)]=pooled_contrast(xm,draws,w)
    return {"status":"EXPLORATORY","knots":knots.tolist(),"common_support":[float(lo),float(hi)],
            "nonlinear_interaction":nonlinear,"assignment_contrasts":contrasts}
