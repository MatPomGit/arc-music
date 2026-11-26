"""Development ordinal CFA: two-step polychorics, diagonal working weights.
Not WLSMV. No robust chi-square or corrected fit indices are implemented.
"""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import least_squares
from ordinal_efa import _ordinal, thresholds, rectangle_prob, polychoric_pair

def pair_moments(x):
    x = _ordinal(x)
    p = x.shape[1]
    cuts = np.stack([thresholds(c) for c in x.T])
    i,j = np.tril_indices(p,-1)
    correlations, information = [], []
    for a,b in zip(i,j):
        rho = polychoric_pair(x[:,a],x[:,b])
        counts = np.bincount(x[:,a]*5+x[:,b],minlength=25).reshape(5,5)
        h = min(1e-4,(1-abs(rho))/4)
        def nll(t):
            return -np.sum(counts*np.log(rectangle_prob(cuts[a],cuts[b],t)))
        curvature = (nll(rho+h)-2*nll(rho)+nll(rho-h))/h**2
        if not np.isfinite(curvature) or curvature <= 0:
            raise ArithmeticError("nonpositive conditional information")
        correlations.append(rho)
        information.append(curvature)
    return np.array(correlations),np.array(information),cuts

@dataclass
class CFAResult:
    loadings: np.ndarray
    phi: np.ndarray
    thresholds: np.ndarray
    uniqueness: np.ndarray
    rms_residual: float
    objective: float
    jacobian_rank: int
    proper: bool

def fit_moments(corr,weights,cuts,domains):
    """Fit a fixed simple structure with standardized latent response variance.

    Weights are observed pairwise information conditional on estimated
    thresholds; they omit threshold-estimation covariance. A development
    approximation only, not the prespecified final robust DWLS estimator.
    """
    domains=np.asarray(domains)
    if domains.ndim!=1 or not np.issubdtype(domains.dtype,np.integer):
        raise ValueError("integer domain assignment required")
    p=len(domains)
    labels,counts=np.unique(domains,return_counts=True)
    k=len(labels)
    if not np.array_equal(labels,np.arange(k)) or np.any(counts<3):
        raise ValueError("contiguous domain labels, at least three items each")
    i,j=np.tril_indices(p,-1)
    corr,weights,cuts=map(lambda a:np.asarray(a,float),(corr,weights,cuts))
    if (corr.shape!=i.shape or weights.shape!=i.shape or cuts.shape!=(p,4)
        or not all(np.isfinite(a).all() for a in (corr,weights,cuts))
        or np.any(np.abs(corr)>=1) or np.any(weights<=0)
        or np.any(np.diff(cuts,axis=1)<=0)):
        raise ValueError("invalid ordinal moments")
    q=k*(k-1)//2
    if len(corr)<=p+q:
        raise ValueError("insufficient model degrees of freedom")
    u,v=np.tril_indices(k,-1)
    anchors=np.array([np.flatnonzero(domains==d)[0] for d in range(k)])
    lower=np.full(p+q,-.995); upper=np.full(p+q,.995)
    lower[anchors]=.005
    lower[p:]=-5; upper[p:]=5
    scale=np.sqrt(weights/weights.mean())
    def unpack(theta):
        l=theta[:p]
        chol=np.eye(k); chol[u,v]=theta[p:]
        chol/=np.linalg.norm(chol,axis=1,keepdims=True)
        return l,chol@chol.T
    def residual(theta):
        l,phi=unpack(theta)
        return scale*(corr-l[i]*l[j]*phi[domains[i],domains[j]])
    fits=[]
    for start in (.45,.7):
        initial=np.r_[np.full(p,start),np.zeros(q)]
        fit=least_squares(residual,initial,bounds=(lower,upper),
                          max_nfev=1000,ftol=1e-9,xtol=1e-9,gtol=1e-9)
        if fit.success and np.isfinite(fit.cost):
            fits.append(fit)
    if not fits:
        raise ArithmeticError("CFA optimization failed")
    fit=min(fits,key=lambda f:f.cost)
    l,phi=unpack(fit.x)
    rank=int(np.linalg.matrix_rank(fit.jac))
    unique=1-l*l
    proper=bool(rank==p+q and np.min(unique)>.01 and
                np.min(np.linalg.eigvalsh(phi))>.01 and not np.any(fit.active_mask))
    raw=corr-l[i]*l[j]*phi[domains[i],domains[j]]
    return CFAResult(l,phi,cuts,unique,float(np.sqrt(np.mean(raw**2))),
                     float(2*fit.cost),rank,proper)

def fit_cfa(x,domains):
    if np.asarray(x).ndim!=2 or np.asarray(x).shape[1]!=len(domains):
        raise ValueError("data and assignment dimension mismatch")
    return fit_moments(*pair_moments(x),domains)

def bootstrap_cfa(x,domains,reps=2000,seed=20261126):
    """Participant bootstrap. Report failures; conditional intervals only.
    Do not issue intervals unless >=95% of fits are proper.
    """
    x=_ordinal(x)
    if reps<20:
        raise ValueError("at least 20 for smoke tests; 2000 for protocol")
    rng=np.random.default_rng(seed)
    values=[]; failures={}
    for _ in range(reps):
        try:
            fit=fit_cfa(x[rng.integers(len(x),size=len(x))],domains)
            if not fit.proper:
                raise ArithmeticError("improper fit")
            values.append(np.r_[fit.loadings,fit.phi[np.tril_indices(len(fit.phi),-1)]])
        except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
            key=str(exc)
            failures[key]=failures.get(key,0)+1
    intervals=np.quantile(values,[.025,.975],axis=0).tolist() if len(values)/reps>=.95 else None
    return {"requested":reps,"proper":len(values),"failures":failures,
            "intervals":intervals,"seed":seed}
