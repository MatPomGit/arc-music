"""Development correlation interval alternatives; no post-hoc method selection."""
import numpy as np
from scipy.stats import norm
from robust_cfa import robust_fit

def fisher_delta(r,se,level=.95):
    """Delta method on atanh(r), not the raw Pearson-correlation formula."""
    r=np.asarray(r,float); se=np.asarray(se,float)
    if r.shape!=se.shape or not np.isfinite(r).all() or not np.isfinite(se).all() or np.any(abs(r)>=1) or np.any(se<=0) or not 0<level<1:
        raise ValueError("invalid correlation or sandwich SE")
    center=np.arctanh(r); width=norm.ppf((1+level)/2)*se/(1-r*r)
    return np.stack([np.tanh(center-width),np.tanh(center+width)],axis=-1)

def compare_intervals(x,domains,reps=2000,seed=20261126,fit=None):
    """Refit thresholds, weights and CFA for every participant bootstrap."""
    if reps<20:
        raise ValueError("at least 20 bootstrap replications")
    x=np.asarray(x,float); p=x.shape[1]
    f=robust_fit(x,domains) if fit is None else fit
    r=f.parameters[p:]
    if not len(r):
        raise ValueError("at least two factors required")
    se=np.sqrt(np.diag(f.covariance)[p:])
    result={"estimate":r.tolist(),"wald":f.intervals[p:].tolist(),
            "fisher_delta":fisher_delta(r,se).tolist(),"requested":reps,
            "percentile":None,"basic":None}
    rng=np.random.default_rng(seed); draws=[]; failures={}
    for _ in range(reps):
        try:
            b=robust_fit(x[rng.integers(len(x),size=len(x))],domains)
            draws.append(b.parameters[p:])
        except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
            key=str(exc); failures[key]=failures.get(key,0)+1
    result.update(proper=len(draws),failures=failures)
    if len(draws)/reps>=.95:
        q=np.quantile(draws,[.025,.975],axis=0)
        result["percentile"]=q.T.tolist()
        result["basic"]=np.column_stack([2*r-q[1],2*r-q[0]]).tolist()
    return result
