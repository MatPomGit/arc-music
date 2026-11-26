"""Exploratory nonlinear moderation, prospective only."""
import numpy as np
from inference import (design, fit_hc3, contrast, impute_pmm,
                       pooled_contrast, target_weights)

from paq_scoring import validate_total

def rcs(value,knots):
    """One nonlinear restricted cubic spline basis with three fixed knots."""
    lo,mid,hi=knots
    if not lo<mid<hi:
        raise ValueError("Non-distinct knots")
    t=np.asarray(value,float)
    pos=lambda k:np.maximum(t-k,0)**3
    return (pos(lo)-(hi-lo)/(hi-mid)*pos(mid)+(mid-lo)/(hi-mid)*pos(hi))/(hi-lo)**2

def spline_sensitivity(arm, paq_total, cov, outcome, m=50, seed=20261126):
    a=np.asarray(arm,float); d=validate_total(paq_total)
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
