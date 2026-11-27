"""Secondary H2/H3 clarity analyses, fixed family and sensitivity grid."""
import numpy as np
from paq_scoring import validate_total
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

def secondary(arm, paq_total, covariates, clarity_t1, m=50, seed=20261126):
    """Same randomised population; covariates: ease, clarity T0, distress, experience, scenario."""
    a,d,c,y=map(lambda v:np.asarray(v,float),(arm,paq_total,covariates,clarity_t1))
    d=validate_total(d)
    n=len(a)
    if a.shape!=(n,) or d.shape!=(n,) or y.shape!=(n,) or c.shape!=(n,5):
        raise ValueError("Invalid dimensions")
    if np.isinf(y).any() or np.any((y<0)|(y>10)):
        raise ValueError("Invalid outcomes")
    if set(np.unique(a))!={0.,1.} or not np.isfinite(c).all() or m<2:
        raise ValueError("Invalid shared baseline schema or imputation count")
    def attempt(cov,coefficient,draw_seed):
        try:
            return {"available":True,**_model(a,d,cov,y,coefficient,m,draw_seed)}
        except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
            return {"available":False,"reason":str(exc),"holm_p":None,"holm_reject":None}
    h2=attempt(c[:,[1,2,4]],2,seed)
    h3=attempt(c,1,seed+1)
    adjusted=holm([h["mar"]["p"] if h["available"] else 1. for h in (h2,h3)])
    for h,p in zip((h2,h3),adjusted):
        if h["available"]:
            h["holm_p"]=float(p)
            h["holm_reject"]=bool(p<.05)
    return {"H2":h2,"H3":h3,"family":"H2-H3","n_randomised":n}
