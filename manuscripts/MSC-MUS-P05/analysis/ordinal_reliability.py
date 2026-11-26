"""Model-implied reliability for standardized congeneric ordinal domains."""
import numpy as np
from scipy.special import ndtr
from ordinal_efa import rectangle_prob

def omega_latent_response(loadings):
    l=np.asarray(loadings,float)
    if l.ndim!=1 or len(l)<3 or not np.isfinite(l).all() or np.any(np.abs(l)>=1):
        raise ValueError("three or more finite interior standardized loadings")
    true=l.sum()**2
    return float(true/(true+np.sum(1-l*l)))

def _ordinal_cov(a,b,rho):
    probs=rectangle_prob(a,b,rho)
    s=np.arange(5.)
    ma=s@np.diff(np.r_[0,ndtr(a),1])
    mb=s@np.diff(np.r_[0,ndtr(b),1])
    return float((s-ma)@probs@(s-mb))

def omega_observed_sum(loadings,cuts):
    """Var(E[sum score | factor])/Var(sum score).
    Assumes conditional independence and a standard normal single factor.
    Diagonal true variance uses two conditionally independent replicates.
    """
    l=np.asarray(loadings,float); cuts=np.asarray(cuts,float)
    omega_latent_response(l)
    if cuts.shape!=(len(l),4) or not np.isfinite(cuts).all() or np.any(np.diff(cuts,axis=1)<=0):
        raise ValueError("ordered finite thresholds required")
    true=0.; observed=0.; s=np.arange(5.)
    for i in range(len(l)):
        p=np.diff(np.r_[0,ndtr(cuts[i]),1])
        observed+=np.sum(p*(s-s@p)**2)
        true+=_ordinal_cov(cuts[i],cuts[i],l[i]**2)
        for j in range(i):
            cov=2*_ordinal_cov(cuts[i],cuts[j],l[i]*l[j])
            true+=cov; observed+=cov
    if observed<=0 or true< -1e-9 or true>observed+1e-9:
        raise ArithmeticError("invalid model-implied variance")
    return float(np.clip(true/observed,0,1))
