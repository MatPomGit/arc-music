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
    diagnostics: dict

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
    row = np.arange(len(i))
    di, dj = domains[i], domains[j]

    def unpack(theta):
        chol = np.eye(k)
        chol[u,v] = theta[p:]
        norms = np.linalg.norm(chol,axis=1)
        chol /= norms[:,None]
        return theta[:p],chol,norms

    def residual(theta):
        l,chol,_ = unpack(theta)
        phi = chol@chol.T
        return scale*(corr-l[i]*l[j]*phi[di,dj])

    def jacobian(theta):
        l,chol,norms = unpack(theta)
        phi = chol@chol.T
        jac = np.zeros((len(i),p+q))
        jac[row,i] = -l[j]*phi[di,dj]
        jac[row,j] = -l[i]*phi[di,dj]
        for index,(domain,column) in enumerate(zip(u,v),p):
            # A factor correlation depends on this parameter only where
            # exactly one item belongs to the affected factor.
            for a,b in ((di,dj),(dj,di)):
                m = (a==domain)&(b!=domain)
                other = b[m]
                derivative = (chol[other,column]-phi[domain,other]*chol[domain,column])/norms[domain]
                jac[m,index] = -l[i[m]]*l[j[m]]*derivative
        return scale[:,None]*jac

    correlated = np.linalg.cholesky(.5*np.ones((k,k))+.5*np.eye(k))
    correlated /= np.diag(correlated).copy()[:,None]
    starts = [(.45,np.zeros(q)),(.7,np.zeros(q)),(.5,correlated[u,v])]
    fits=[]
    for loading,correlation in starts:
        initial=np.r_[np.full(p,loading),correlation]
        fit=least_squares(residual,initial,jac=jacobian,bounds=(lower,upper),
                          max_nfev=1000,ftol=1e-9,xtol=1e-9,gtol=1e-9)
        if fit.success and np.isfinite(fit.cost):
            fits.append(fit)
    if not fits:
        raise ArithmeticError("CFA optimization failed")
    fit=min(fits,key=lambda f:f.cost)
    l,chol,_ = unpack(fit.x)
    phi = chol@chol.T
    singular = np.linalg.svd(fit.jac,compute_uv=False)
    rank = int(np.linalg.matrix_rank(fit.jac))
    unique = 1-l*l
    min_unique = float(np.min(unique))
    min_eigenvalue = float(np.min(np.linalg.eigvalsh(phi)))
    active = np.flatnonzero(fit.active_mask).tolist()
    flags = []
    if rank!=p+q:
        flags.append("rank_deficient")
    if min_unique<=.01:
        flags.append("near_heywood")
    if min_eigenvalue<=.01:
        flags.append("near_singular_factors")
    if active:
        flags.append("active_bound")
    diagnostics = dict(flags=flags, min_uniqueness=min_unique,
                       min_factor_eigenvalue=min_eigenvalue, active_parameters=active,
                       jacobian_condition=float(singular[0]/singular[-1]) if rank==p+q else None,
                       largest_absolute_factor_correlation=float(np.max(abs(phi[u,v]))) if q else None,
                       lowest_absolute_loading=float(np.min(abs(l))),
                       converged_starts=len(fits),
                       objective_range=2*(max(f.cost for f in fits)-fit.cost))
    raw=corr-l[i]*l[j]*phi[di,dj]
    return CFAResult(l,phi,cuts,unique,float(np.sqrt(np.mean(raw**2))),
                     float(2*fit.cost),rank,not flags,diagnostics)

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
