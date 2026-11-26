"""Two-step ordinal DWLS with empirical influence-function covariance.
Development estimator; moment-matched fit test is not certified WLSMV.
Complete independent records only. No silent smoothing or pseudoinverse.
"""
from dataclasses import dataclass
import numpy as np
from scipy.special import ndtr
from scipy.stats import norm, chi2
from ordinal_efa import _ordinal, thresholds, rectangle_prob, polychoric_pair
from ordinal_cfa import fit_moments

@dataclass
class OrdinalMoments:
    correlations: np.ndarray
    cuts: np.ndarray
    influence: np.ndarray

def _score(a,b,rho,h=1e-4):
    return (np.log(rectangle_prob(a,b,rho+h))-
            np.log(rectangle_prob(a,b,rho-h)))/(2*h)

def robust_moments(x):
    """Estimate joint correlation IF, accounting for estimated marginal cuts.

    IF(tau) = (I[Y<=k]-Phi(tau))/phi(tau).
    For pairwise likelihood score s, IF(rho) = (s + B IF(tau))/A,
    A=-mean(ds/drho), B=mean(ds/dtau); evaluate derivatives numerically.
    Center each empirical influence column. Full cross-pair covariance is
    retained, including pairs sharing no items.
    """
    x=_ordinal(x)
    n,p=x.shape
    cuts=np.stack([thresholds(c) for c in x.T])
    threshold_if=((x[:,:,None]<=np.arange(4))-ndtr(cuts)[None,:,:])/norm.pdf(cuts)[None,:,:]
    ii,jj=np.tril_indices(p,-1)
    correlations=np.empty(len(ii)); influence=np.empty((n,len(ii)))
    h=1e-4
    for m,(i,j) in enumerate(zip(ii,jj)):
        a,b=cuts[i],cuts[j]; xi,xj=x[:,i],x[:,j]
        rho=polychoric_pair(xi,xj)
        score=_score(a,b,rho,h)
        info=-np.mean(((_score(a,b,rho+h,h)-_score(a,b,rho-h,h))/(2*h))[xi,xj])
        if not np.isfinite(info) or info<=0:
            raise ArithmeticError("nonpositive pair information")
        correction=np.zeros(n)
        for side,t in enumerate((a,b)):
            for k in range(4):
                step=np.zeros(4); step[k]=h
                if side==0:
                    derivative=(_score(t+step,b,rho,h)-_score(t-step,b,rho,h))/(2*h)
                else:
                    derivative=(_score(a,t+step,rho,h)-_score(a,t-step,rho,h))/(2*h)
                coefficient=np.mean(derivative[xi,xj])
                correction+=coefficient*threshold_if[:,(i,j)[side],k]
        values=(score[xi,xj]+correction)/info
        correlations[m]=rho
        influence[:,m]=values-values.mean()
    if not np.isfinite(influence).all():
        raise ArithmeticError("nonfinite influence function")
    return OrdinalMoments(correlations,cuts,influence)

def _model_jacobian(loadings,phi,domains):
    l=np.asarray(loadings); d=np.asarray(domains)
    p=len(l); k=len(phi); i,j=np.tril_indices(p,-1)
    a,b=np.tril_indices(k,-1)
    J=np.zeros((len(i),p+len(a))); rows=np.arange(len(i))
    J[rows,i]=l[j]*phi[d[i],d[j]]
    J[rows,j]=l[i]*phi[d[i],d[j]]
    for m,(u,v) in enumerate(zip(a,b)):
        mask=((d[i]==u)&(d[j]==v))|((d[i]==v)&(d[j]==u))
        J[mask,p+m]=l[i[mask]]*l[j[mask]]
    return l[i]*l[j]*phi[d[i],d[j]],J

@dataclass
class RobustResult:
    fit: object
    parameters: np.ndarray
    covariance: np.ndarray
    intervals: np.ndarray
    statistic: float
    scale: float
    effective_df: float
    p_value: float
    nominal_df: int
    sample_size: int
    parameter_influence: np.ndarray
    baseline_statistic: float
    baseline_expected: float
    baseline_df: int
    model_expected: float

def robust_fit(x,domains):
    """Diagonal inverse IF-variance weights, sandwich and residual test.

    Covariance = (J'WJ)^-1 J'W Gamma WJ (J'WJ)^-1 / n.
    Residual quadratic form uses a two-moment scaled chi-square approximation.
    Effective df need not be integer. This is not a robust CFI/TLI/RMSEA
    implementation or an exact reproduction of commercial WLSMV.
    """
    m=robust_moments(x); n=len(x)
    variances=np.sum(m.influence*m.influence,axis=0)/(n-1)
    if np.any(variances<=1e-10):
        raise ArithmeticError("degenerate moment variance")
    w=1/variances
    fit=fit_moments(m.correlations,w,m.cuts,domains)
    if not fit.proper:
        raise ArithmeticError("improper DWLS fit")
    expected,J=_model_jacobian(fit.loadings,fit.phi,domains)
    bread=J.T@(w[:,None]*J)
    if np.linalg.cond(bread)>1e10:
        raise ArithmeticError("ill-conditioned information")
    D=np.linalg.solve(bread,J.T*w)
    param_if=m.influence@D.T
    covariance=param_if.T@param_if/(n*(n-1))
    u,v=np.tril_indices(len(fit.phi),-1)
    estimates=np.r_[fit.loadings,fit.phi[u,v]]
    se=np.sqrt(np.diag(covariance))
    intervals=np.column_stack((estimates-1.959963984540054*se,estimates+1.959963984540054*se))
    residual_if=(m.influence-param_if@J.T)*np.sqrt(w)
    # Trace and Frobenius norm without inversion of a possibly singular Gamma.
    A=residual_if.T@residual_if/(n-1)
    tr=np.trace(A); tr2=np.sum(A*A)
    if min(tr,tr2)<=1e-10:
        raise ArithmeticError("degenerate residual test")
    statistic=n*np.sum(w*(m.correlations-expected)**2)
    scale=tr2/tr; df=tr*tr/tr2
    return RobustResult(fit,estimates,covariance,intervals,float(statistic),
                        float(scale),float(df),float(chi2.sf(statistic/scale,df)),
                        len(w)-J.shape[1],n,param_if,
                        float(n*np.sum(w*m.correlations**2)),
                        float(np.sum(variances*w)),len(w),float(tr))
