"""P06 missing-outcome sensitivity; not an estimator for unlogged sessions."""
import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.optimize import minimize
from inference import PREDICTORS, fit_arrays

def weighted_within(g,x,y,w):
    g=np.asarray(g); x=np.asarray(x,float); y=np.asarray(y,float); w=np.asarray(w,float)
    if not (len(g)==len(x)==len(y)==len(w)) or not np.isfinite(w).all() or (w<=0).any():
        raise ValueError("Invalid weights")
    _,idx=np.unique(g,return_inverse=True)
    count=np.bincount(idx); keep=count[idx]>=2
    g,x,y,w=g[keep],x[keep],y[keep],w[keep]
    _,idx=np.unique(g,return_inverse=True)
    G=len(np.unique(g))
    if G<10: raise ValueError("Too few clusters")
    total=np.bincount(idx,weights=w)
    xm=np.zeros((G,x.shape[1])); ym=np.zeros(G)
    np.add.at(xm,idx,x*w[:,None]); np.add.at(ym,idx,y*w)
    x=x-xm[idx]/total[idx,None]; y=y-ym[idx]/total[idx]
    xw=x*np.sqrt(w[:,None]); yw=y*np.sqrt(w)
    if np.linalg.matrix_rank(xw)<x.shape[1]: raise ValueError("Rank deficient weighted design")
    return np.linalg.lstsq(xw,yw,rcond=None)[0]

def observation_probability(x, observed):
    x=np.asarray(x,float); observed=np.asarray(observed,int)
    if not np.isfinite(x).all() or not np.isin(observed,[0,1]).all():
        raise ValueError("Invalid observation model input")
    if len(np.unique(observed))!=2: raise ValueError("Need observed and missing cases")
    mean=x.mean(axis=0); scale=x.std(axis=0)
    z=np.column_stack([np.ones(len(x)),(x-mean)/np.where(scale>0,scale,1)])
    # Weak fixed ridge on slopes guards separation; intercept not penalized.
    def objective(b):
        v=z@b
        return np.logaddexp(0,v).sum()-observed@v+.5*np.sum(b[1:]**2)
    def gradient(b):
        return z.T@(expit(z@b)-observed)+np.r_[0,b[1:]]
    opt=minimize(objective,np.zeros(z.shape[1]),jac=gradient,method="BFGS")
    if not opt.success and np.linalg.norm(gradient(opt.x))>1e-5:
        raise ValueError("Observation model did not converge")
    return expit(z@opt.x)

def sensitivity(frame):
    # Contract: one row per eligible session with valid pre/start/end and complete
    # predictors; y missing denotes unavailable or out-of-window follow-up.
    g=frame.participant_id.to_numpy()
    x=frame[PREDICTORS].to_numpy(float)
    y=frame.interference.to_numpy(float)
    observed=np.isfinite(y)
    if not np.isfinite(x).all() or not np.isin(y[observed],np.arange(11)).all():
        raise ValueError("Invalid scores or predictors")
    p=observation_probability(x,observed)
    w=1/np.maximum(p[observed],.05)
    ipw={}
    for cap in [10,20]:
        ipw[str(cap)]=float(weighted_within(g[observed],x[observed],y[observed],np.minimum(w,cap))[0])
    complete=fit_arrays(g[observed],x[observed],y[observed])
    b=np.asarray(complete["estimate"])
    # Estimate participant intercept from observed residuals only. People
    # without observed outcomes cannot be included in this sensitivity target.
    offsets=pd.Series(y[observed]-x[observed]@b).groupby(g[observed]).mean()
    included=np.isin(g,offsets.index)
    pred=np.asarray([offsets.get(i,np.nan) for i in g])+x@b
    # Bounded deterministic mean-shift scenarios, NOT multiple imputation.
    shifts={}
    for shift in [-2,-1,0,1,2]:
        # Also stress differential missing outcomes by avoidance, using its
        # within-person deviation to avoid conflating between-person effects.
        a=x[:,0]
        ac=a-pd.Series(a).groupby(g).transform("mean").to_numpy()
        for differential in [-1,0,1]:
            filled=np.where(observed,y,np.clip(pred+shift+differential*ac/2,0,10))
            key=f"{shift:+d}/{differential:+d}"
            shifts[key]=float(fit_arrays(g[included],x[included],filled[included])["estimate"][0])
    return {"complete_case":complete["estimate"][0],"ipw":ipw,
            "pattern_mean_shifts":shifts,"observation_rate":float(observed.mean()),
            "min_probability":float(p.min()),"max_raw_weight":float(w.max()),
            "fraction_probability_below_005":float((p<.05).mean()),
            "participants_without_observed_outcome":int(len(set(g)-set(g[observed])))}

def cluster_bootstrap(frame,reps=499,seed=2606):
    if reps<1: raise ValueError("Positive reps required")
    rng=np.random.default_rng(seed)
    groups=[v for _,v in frame.groupby("participant_id",sort=False)]
    original=sensitivity(frame); values=[]; failures=0
    for _ in range(reps):
        sample=pd.concat([groups[j].assign(participant_id=i)
                          for i,j in enumerate(rng.integers(len(groups),size=len(groups)))],
                         ignore_index=True)
        try:
            values.append(sensitivity(sample))
        except (ValueError,np.linalg.LinAlgError):
            failures+=1
    def ci(series):
        return np.quantile(series,[.025,.975]).tolist() if len(series) else None
    return {"point":original,"valid":len(values),"failed":failures,"reps":reps,
            "ci_reliable":len(values)>=.9*reps and reps>=499,
            "ipw_ci":{k:ci([v["ipw"][k] for v in values]) for k in original["ipw"]},
            "shift_ci":{k:ci([v["pattern_mean_shifts"][k] for v in values])
                         for k in original["pattern_mean_shifts"]}}
