"""Development complete-record selection sensitivity, not item-level imputation."""
from dataclasses import dataclass
import numpy as np
from scipy.special import expit, ndtri
from scipy.optimize import minimize, minimize_scalar, brentq
from ordinal_efa import _ordinal, rectangle_prob
from ordinal_cfa import fit_moments

def inputs(x,z):
    x=np.asarray(x,float); z=np.asarray(z,float)
    if x.ndim!=2 or len(x)<30 or z.ndim!=2 or len(z)!=len(x) or not np.isfinite(z).all():
        raise ValueError("valid matrix and fully observed auxiliaries required")
    if np.isinf(x).any() or not np.isin(x[np.isfinite(x)],np.arange(5)).all():
        raise ValueError("invalid ordinal data")
    return x,z,np.isfinite(x).all(axis=1)

def propensity(x,z):
    """Logistic probability of a complete record, estimated in all respondents."""
    x,z,c=inputs(x,z)
    if c.all():
        return np.ones(len(x))
    if c.sum()<30 or (~c).sum()<5:
        raise ValueError("insufficient complete or incomplete observations")
    design=np.column_stack([np.ones(len(z)),z])
    if np.linalg.matrix_rank(design)!=design.shape[1]:
        raise ValueError("rank-deficient auxiliary design")
    y=c.astype(float)
    def loss(b):
        eta=design@b
        return float(np.sum(np.logaddexp(0,eta)-y*eta)),design.T@(expit(eta)-y)
    fit=minimize(loss,np.zeros(design.shape[1]),jac=True,method="BFGS",
                 options={"gtol":1e-6,"maxiter":500})
    if not fit.success and np.linalg.norm(fit.jac,np.inf)>1e-4:
        raise ArithmeticError("propensity optimization failed")
    prob=expit(design@fit.x)
    if not np.isfinite(prob).all() or prob.min()<.01 or prob.max()>1-1e-8:
        raise ArithmeticError("positivity/separation warning; no automatic clipping")
    return prob

def weighted_moments(x,w):
    x=_ordinal(x); w=np.asarray(w,float)
    if w.shape!=(len(x),) or not np.isfinite(w).all() or np.any(w<=0):
        raise ValueError("positive finite weights required")
    w=w/w.mean()
    p=x.shape[1]
    cuts=np.stack([ndtri(np.cumsum(np.bincount(c,weights=w,minlength=5))[:-1]/w.sum()) for c in x.T])
    correlations=[]; information=[]
    for i,j in zip(*np.tril_indices(p,-1)):
        a,b=cuts[i],cuts[j]
        counts=np.bincount(x[:,i]*5+x[:,j],weights=w,minlength=25).reshape(5,5)
        def loss(r):
            return -float(np.sum(counts*np.log(rectangle_prob(a,b,r))))
        f=minimize_scalar(loss,bounds=(-.98,.98),method="bounded",options={"xatol":1e-6})
        if not f.success or abs(f.x)>=.979:
            raise ArithmeticError("weighted polychoric boundary or failed fit")
        h=1e-4
        info=(loss(f.x+h)-2*loss(f.x)+loss(f.x-h))/h**2
        if not np.isfinite(info) or info<=0:
            raise ArithmeticError("invalid weighted information")
        correlations.append(f.x); information.append(info)
    return np.array(correlations),np.array(information),cuts

@dataclass
class SelectionFit:
    fit: object
    complete_n: int
    ess: float
    min_probability: float
    max_weight: float
    delta: float

def selection_fit(x,z,domains,delta=0.,prob=None):
    """MAR inverse probability weights; MNAR exponential tilt by auxiliary stratum.

    Within stratum Z, posit f(Y|incomplete,Z) proportional to
    f(Y|complete,Z) exp(delta*t(Y)), with t=(first domain mean-2)/2.
    Delta is an unidentified sensitivity parameter. Complete records represent
    both complete and incomplete strata. Discrete strata are required for tilt.
    Weighted CFA uses conditional pair-information working weights, not WLSMV.
    """
    x,z,c=inputs(x,z)
    if not np.isfinite(delta) or abs(delta)>3:
        raise ValueError("delta must be in [-3,3]")
    prob=propensity(x,z) if prob is None else np.asarray(prob,float)
    if prob.shape!=(len(x),) or not np.isfinite(prob).all() or np.any(prob<.01) or np.any(prob>1):
        raise ValueError("invalid complete-record probabilities")
    if c.sum()<30:
        raise ValueError("insufficient complete records")
    d=np.asarray(domains)
    if d.shape!=(x.shape[1],) or not np.any(d==0):
        raise ValueError("invalid domains")
    pc=prob[c]; w=1/pc
    if delta!=0:
        if np.ptp(prob)==0 and c.all():
            raise ValueError("no incomplete records to tilt")
        strata,labels=np.unique(z,axis=0,return_inverse=True)
        if len(strata)>20:
            raise ValueError("MNAR tilt requires few discrete prespecified strata")
        t=(x[c][:,d==0].mean(axis=1)-2)/2
        tilt=np.exp(delta*t)
        for group in range(len(strata)):
            mask=labels[c]==group
            if mask.sum()<10:
                raise ValueError("sparse complete auxiliary stratum")
            if np.ptp(pc[mask])>1e-8:
                raise ValueError("tilt requires probabilities constant within stratum")
            tilt[mask]/=tilt[mask].mean()
        w=1+(1/pc-1)*tilt
    fit=fit_moments(*weighted_moments(x[c],w),d)
    if not fit.proper:
        raise ArithmeticError("improper weighted CFA")
    ess=w.sum()**2/(w@w)
    return SelectionFit(fit,int(c.sum()),float(ess),float(pc.min()),float(w.max()),float(delta))

def bootstrap_selection(x,z,domains,delta=0.,reps=2000,seed=20261129):
    """Refit propensity and CFA in each participant bootstrap."""
    x,z,_=inputs(x,z)
    if reps<20:
        raise ValueError("at least 20 bootstrap replications")
    rng=np.random.default_rng(seed); estimates=[]; failures={}
    for _ in range(reps):
        take=rng.integers(len(x),size=len(x))
        try:
            fit=selection_fit(x[take],z[take],domains,delta).fit
            estimates.append(np.r_[fit.loadings,fit.phi[np.tril_indices(len(fit.phi),-1)]])
        except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
            key=str(exc); failures[key]=failures.get(key,0)+1
    intervals=np.quantile(estimates,[.025,.975],axis=0).tolist() if len(estimates)/reps>=.95 else None
    return {"requested":reps,"proper":len(estimates),"failures":failures,"intervals":intervals,"delta":delta}

def simulate_selection(n,k,items,loading,rho,mechanism,rate,rng):
    """Known selection; selected incomplete records have first domain missing."""
    if mechanism not in {"MCAR","MAR","MNAR"} or not 0<rate<.8:
        raise ValueError("invalid selection mechanism")
    phi=np.full((k,k),rho); np.fill_diagonal(phi,1.)
    latent=rng.multivariate_normal(np.zeros(k),phi,size=n)
    z=(latent[:,0]+rng.normal(size=n)>0.).astype(float)[:,None]
    y=np.digitize(loading*np.repeat(latent,items,axis=1)+np.sqrt(1-loading**2)*rng.normal(size=(n,k*items)),[-.85,-.25,.25,.85]).astype(float)
    predictor=np.zeros(n) if mechanism=="MCAR" else 1.5*z[:,0]
    if mechanism=="MNAR":
        predictor=predictor+2*((y[:,:items].mean(axis=1)-2)/2)
    intercept=brentq(lambda a:expit(a+predictor).mean()-rate,-20,20)
    miss_prob=expit(intercept+predictor)
    miss=rng.random(n)<miss_prob
    observed=y.copy(); observed[miss,:items]=np.nan
    return y,observed,z,1-miss_prob
