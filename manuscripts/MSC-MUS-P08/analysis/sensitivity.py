"""P08 outcome sensitivity. Scenario contrasts, not identified causal effects."""
import numpy as np
from scipy.special import expit
from scipy.optimize import minimize
from inference import design,fit_arrays

CELLS=[(0,0),(0,1),(1,0),(1,1)]
CONTRASTS={"authority":np.array([-.5,-.5,.5,.5]),"execution":np.array([-.5,.5,-.5,.5]),"interaction":np.array([1.,-1.,-1.,1.])}

def cell_bounds(d,outcome):
    lows=[];highs=[]
    for a,e in CELLS:
        y=d.loc[(d.authority==a)&(d.manual==e),outcome]
        if not len(y):raise ValueError("Empty assigned cell")
        lows.append(float(y.sum()/len(y)))
        highs.append(float((y.sum()+10*y.isna().sum())/len(y)))
    lo,hi=np.array(lows),np.array(highs)
    return {name:[float(np.where(c>=0,c*lo,c*hi).sum()),float(np.where(c>=0,c*hi,c*lo).sum())] for name,c in CONTRASTS.items()}

def weights(x,observed):
    if observed.all():return np.ones(len(x))
    if not observed.any():raise ValueError("No observed outcomes")
    scale=x[:,1:].std(axis=0);scale=np.where(scale>0,scale,1)
    z=np.column_stack([np.ones(len(x)),(x[:,1:]-x[:,1:].mean(axis=0))/scale])
    y=observed.astype(float)
    def obj(b):
        v=z@b;return np.logaddexp(0,v).sum()-y@v+.5*(b[1:]@b[1:])
    def grad(b):return z.T@(expit(z@b)-y)+np.r_[0,b[1:]]
    opt=minimize(obj,np.zeros(z.shape[1]),jac=grad,method="BFGS")
    if not opt.success and np.linalg.norm(grad(opt.x))>1e-5:raise ValueError("Availability model failed")
    return expit(z@opt.x)

def assess(d,outcome):
    if not len(d):raise ValueError("Empty assigned sample")
    x=design(d);y=d[outcome].to_numpy(float);k=np.isfinite(y)
    result={"observed":int(k.sum()),"missing":int((~k).sum()),
            "unadjusted_hypothetical_bounds":cell_bounds(d,outcome)}
    try:
        # Validate all four observed cells and rank using primary estimator.
        fit_arrays(x[k],y[k])
        p=weights(x,k);raw=1/np.maximum(p[k],.05)
        ipw={}
        for cap in (10,20):
            w=np.minimum(raw,cap);a=x[k]*np.sqrt(w[:,None]);b=y[k]*np.sqrt(w)
            coef=np.linalg.lstsq(a,b,rcond=None)[0]
            ipw[str(cap)]={name:float(coef[j]) for j,name in enumerate(CONTRASTS,1)}
        result["ipw"]={"point_estimates":ipw,"minimum_probability":float(p.min()),"capped_fraction_10":float((raw>10).mean())}
        beta=np.linalg.lstsq(x[k],y[k],rcond=None)[0]
        pred=x@beta
        # Apply additive shift and contrasts of missing outcomes by assigned authority
        # and execution, without altering observed outcomes.
        scenarios={}
        for common in (-2,0,2):
            for authority in (-2,0,2):
                for interaction in (-2,0,2):
                    fill=np.where(k,y,np.clip(pred+common+authority*x[:,1]+interaction*x[:,3],0,10))
                    coef=np.linalg.lstsq(x,fill,rcond=None)[0]
                    scenarios[f"{common}/{authority}/{interaction}"]={name:float(coef[j]) for j,name in enumerate(CONTRASTS,1)}
        result["shift_scenarios"]=scenarios
    except (ValueError,np.linalg.LinAlgError) as exc:result["unavailable"]=str(exc)
    return result
