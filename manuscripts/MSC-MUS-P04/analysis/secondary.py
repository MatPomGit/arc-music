"""Secondary H2/H3 clarity analyses, fixed family and sensitivity grid."""
import numpy as np
from inference import (design,fit_hc3,contrast,impute_pmm,pooled_contrast,
                       shift_imputed,availability)

def holm(p):
    p=np.asarray(p,float)
    if p.ndim!=1 or not len(p) or not np.isfinite(p).all() or np.any((p<0)|(p>1)):
        raise ValueError("Invalid p-values")
    order=np.argsort(p)
    out=np.empty_like(p)
    out[order]=np.minimum(1,np.maximum.accumulate(p[order]*np.arange(len(p),0,-1)))
    return out

def _model(arm, moderator, cov, y, coefficient, m, seed):
    x=design(arm,moderator,cov)
    # Imputation preserves arm-specific slopes; reduced analysis is additive.
    z=x[:,[0,1,2,*range(4,x.shape[1])]]
    w=np.zeros(z.shape[1]); w[coefficient]=1
    b,v,df=fit_hc3(z,y)
    completed=impute_pmm(x,y,m,seed)
    pooled=pooled_contrast(z,completed,w)
    return {"n_baseline_eligible":len(y),"n_outcomes":int(np.isfinite(y).sum()),
            "complete_outcome":contrast(b,v,df,w),"mar":pooled,
            "availability":availability(x,y),
            "sensitivity":[{"offset_control":i,"offset_scaffold":j,"differential_slope":s,
                 **pooled_contrast(z,shift_imputed(x,y,completed,i,j,s),w)}
                 for i in (-2,0,2) for j in (-2,0,2) for s in (-1,0,1)]}

def secondary(arm, nddf, ndif, covariates, clarity_t1, m=50, seed=20261126):
    """covariate order: expression ease, clarity T0, distress, experience, scenario."""
    a,d,f,c,y=map(lambda v:np.asarray(v,float),(arm,nddf,ndif,covariates,clarity_t1))
    n=len(a)
    if a.shape!=(n,) or d.shape!=(n,) or f.shape!=(n,) or y.shape!=(n,) or c.shape!=(n,5):
        raise ValueError("Invalid dimensions")
    if np.isinf(f).any() or np.isinf(y).any() or np.any((y<0)|(y>10)):
        raise ValueError("Invalid outcomes or baseline scores")
    # H2: N-DIF association, controlling for baseline clarity, assignment, distress, scenario.
    valid=np.isfinite(f)
    h2=_model(a[valid],f[valid],c[valid][:,[1,2,4]],y[valid],2,m,seed)
    h2["excluded_missing_ndif"]=int((~valid).sum())
    # H3: assignment effect, controlling for N-DDF and the five baseline covariates.
    h3=_model(a,d,c,y,1,m,seed+1)
    adjusted=holm([h2["mar"]["p"],h3["mar"]["p"]])
    for h,p in zip((h2,h3),adjusted):
        h["holm_p"]=float(p)
        h["holm_reject"]=bool(p<.05)
    return {"H2":h2,"H3":h3,"family":"H2-H3","n_randomised":n}
