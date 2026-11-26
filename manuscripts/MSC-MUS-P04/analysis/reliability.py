"""Ordinal one-factor moment model for reliability of the actual six-item sum.
Conditional independence and normal factor are assumptions; not a diagnostic tool.
"""
import numpy as np
from scipy.special import ndtr, ndtri
from scipy.optimize import least_squares
from numpy.polynomial.hermite import hermgauss
from paq_scoring import validate_items

def conditional_moments(thresholds, loadings, nodes):
    """Standard-normal latent responses, residual variance 1-loading**2."""
    thresholds=np.asarray(thresholds,float); loadings=np.asarray(loadings,float)
    cdf=ndtr((thresholds[None,:,:]-nodes[:,None,None]*loadings[None,:,None])
             /np.sqrt(1-loadings**2)[None,:,None])
    probs=np.diff(np.concatenate((np.zeros((*cdf.shape[:2],1)),cdf,
                                  np.ones((*cdf.shape[:2],1))),axis=2),axis=2)
    categories=np.arange(1,8)
    mean=probs@categories
    variance=probs@(categories**2)-mean**2
    return mean,np.maximum(variance,0)

def omega_from_moments(mean,variance,weights):
    total=mean.sum(axis=1)
    true=float(weights@(total**2)-(weights@total)**2)
    error=float(weights@variance.sum(axis=1))
    if true< -1e-10 or error<=0:
        raise ValueError("Invalid model-implied variance")
    true=max(true,0.)
    return true/(true+error),true,error

def fit_ordinal(items,min_n=100):
    x=validate_items(items)
    x=x[np.isfinite(x).all(axis=1)]
    n=len(x)
    if n<min_n:
        raise ValueError("Insufficient complete cases")
    counts=np.array([np.bincount(x[:,i].astype(int),minlength=8)[1:8] for i in range(6)])
    if (counts==0).any():
        raise ValueError("All seven response categories required per item")
    thresholds=ndtri(np.cumsum(counts,axis=1)[:,:6]/n)
    cov=np.cov(x,rowvar=False,ddof=0)
    sd=np.sqrt(np.diag(cov))
    ii,jj=np.triu_indices(6,1)
    nodes,weights=hermgauss(41)
    nodes=nodes*np.sqrt(2); weights=weights/np.sqrt(np.pi)
    def residual(loadings):
        m,_=conditional_moments(thresholds,loadings,nodes)
        centered=m-weights@m
        pred=centered.T@(weights[:,None]*centered)
        return (pred[ii,jj]-cov[ii,jj])/(sd[ii]*sd[jj])
    # Positive loading direction is prespecified for the additive PAQ-S.
    fits=[least_squares(residual,np.full(6,start),bounds=(.001,.995),
                        ftol=1e-9,xtol=1e-9,gtol=1e-9,max_nfev=300)
          for start in (.35,.75)]
    fit=min((f for f in fits if f.success),key=lambda f:f.cost,default=None)
    if fit is None:
        raise ValueError("Ordinal moment fit failed")
    if np.any((fit.x<.002)|(fit.x>.994)):
        raise ValueError("Boundary loading; model inadmissible")
    m,v=conditional_moments(thresholds,fit.x,nodes)
    omega,true,error=omega_from_moments(m,v,weights)
    alpha=6/5*(1-np.trace(cov)/cov.sum())
    resid=residual(fit.x)
    return {"omega_categorical":omega,"alpha":float(alpha),"n_complete":n,
            "loadings":fit.x.tolist(),"model_sum_variance":true+error,
            "observed_sum_variance":float(cov.sum()),
            "rms_off_diagonal_correlation_residual":float(np.sqrt(np.mean(resid**2))),
            "max_abs_correlation_residual":float(np.max(np.abs(resid))),
            "category_counts":counts.tolist()}

def reliability(items,reps=1000,seed=20261129,min_n=100):
    if reps<2:
        raise ValueError("At least two bootstrap replications required")
    x=validate_items(items)
    complete=x[np.isfinite(x).all(axis=1)]
    base=fit_ordinal(complete,min_n)
    rng=np.random.default_rng(seed)
    values=[]; failures={}
    for _ in range(reps):
        try:
            fit=fit_ordinal(complete[rng.integers(len(complete),size=len(complete))],min_n)
            values.append(fit["omega_categorical"])
        except (ValueError,np.linalg.LinAlgError) as exc:
            key=str(exc)
            failures[key]=failures.get(key,0)+1
    valid=len(values)
    return {**base,"n_total":len(x),"n_incomplete":len(x)-len(complete),
            "bootstrap_requested":reps,"bootstrap_valid":valid,
            "bootstrap_failures":failures,"seed":seed,
            "omega_percentile95":np.quantile(values,[.025,.975]).tolist()
            if valid>=.95*reps else None,
            "status":"MODEL_DEPENDENT_INTERVAL" if valid>=.95*reps else "INTERVAL_NOT_ESTIMABLE"}
