"""Separate missing exposure and outcome sensitivity; no causal correction claims."""
import numpy as np
from scipy.special import expit,logit
from scipy.optimize import minimize
from inference import PRED,fit_arrays

def probability(x,z):
    x=np.asarray(x,float);z=np.asarray(z,int)
    if not np.isfinite(x).all() or not np.isin(z,[0,1]).all() or len(z)!=len(x):
        raise ValueError("Invalid logistic input")
    if len(np.unique(z))<2:raise ValueError("Both classes required")
    s=x.std(axis=0)
    a=np.column_stack([np.ones(len(x)),(x-x.mean(axis=0))/np.where(s>0,s,1)])
    def obj(b):
        v=a@b;return np.logaddexp(0,v).sum()-z@v+.5*np.sum(b[1:]**2)
    def grad(b):return a.T@(expit(a@b)-z)+np.r_[0,b[1:]]
    opt=minimize(obj,np.zeros(a.shape[1]),jac=grad,method="BFGS")
    if not opt.success and np.linalg.norm(grad(opt.x))>1e-5:raise ValueError("Logistic fit failed")
    mean=x.mean(axis=0); scale=np.where(s>0,s,1)
    def predict(new):
        new=np.asarray(new,float)
        return expit(np.column_stack([np.ones(len(new)),(new-mean)/scale])@opt.x)
    return predict

def weighted_slope(g,x,y,w):
    _,g=np.unique(g,return_inverse=True)
    total=np.bincount(g); exposed=np.bincount(g,weights=x[:,0])
    k=(exposed[g]>0)&(exposed[g]<total[g])
    g,x,y,w=g[k],x[k],y[k],w[k]
    _,g=np.unique(g,return_inverse=True)
    if len(np.unique(g))<10:raise ValueError("Too few switcher clusters")
    total=np.bincount(g,weights=w)
    xm=np.zeros((len(total),x.shape[1]));ym=np.zeros(len(total))
    np.add.at(xm,g,x*w[:,None]);np.add.at(ym,g,y*w)
    x=(x-xm[g]/total[g,None])*np.sqrt(w[:,None]);y=(y-ym[g]/total[g])*np.sqrt(w)
    if np.linalg.matrix_rank(x)<x.shape[1]:raise ValueError("Rank deficient weighted design")
    return np.linalg.lstsq(x,y,rcond=None)[0]

def assess(d,draws=100,seed=2708):
    if draws<1:raise ValueError("Positive draws required")
    a=d.loc[d.baseline_valid].copy()
    if not len(a):raise ValueError("No valid baselines")
    g=a.participant_id.to_numpy(); cov=a[PRED[1:]].to_numpy(float)
    e=a.exposure_valid.to_numpy(bool); o=a.outcome60_valid.to_numpy(bool)
    c=np.where(e,a.creation_first_hour, np.nan).astype(float)
    y=np.where(o,a.valence60,np.nan)
    complete=e&o
    out={"valid_baselines":len(a),"unknown_exposure":int((~e).sum()),
         "unknown_outcome":int((~o).sum()),"both_missing":int((~e&~o).sum()),
         "outcome_only_missing":int((e&~o).sum()),"exposure_only_missing":int((~e&o).sum())}
    x=np.column_stack([c,cov])
    def attempt(name,fn):
        try:out[name]=fn()
        except (ValueError,np.linalg.LinAlgError) as exc:out[name]={"unavailable":str(exc)}
    def weights():
        pe=probability(cov,e)(cov) if not e.all() else np.ones(len(a))
        po=probability(x[e],o[e])(x[e]) if not o[e].all() else np.ones(e.sum())
        p=pe[e]*po;raw=1/np.maximum(p[o[e]],.05)
        if not len(raw):raise ValueError("No complete windows")
        return {"cap10":float(weighted_slope(g[complete],x[complete],y[complete],np.minimum(raw,10))[0]),
                "cap20":float(weighted_slope(g[complete],x[complete],y[complete],np.minimum(raw,20))[0]),
                "min_joint_probability":float(p.min()),"capped_fraction_10":float((raw>10).mean())}
    def outcome_shifts():
        # Restrict to known exposure; participants with at least one observed outcome.
        # Fit on observed switchers; estimate participant offsets from all observed known exposures.
        _,ix=np.unique(g[complete],return_inverse=True)
        counts=np.bincount(ix);ex=np.bincount(ix,weights=c[complete])
        switch=(ex[ix]>0)&(ex[ix]<counts[ix])
        b=weighted_slope(g[complete][switch],x[complete][switch],y[complete][switch],np.ones(switch.sum()))
        ids,idx=np.unique(g[complete],return_inverse=True)
        offsets=np.bincount(idx,weights=y[complete]-x[complete]@b)/np.bincount(idx)
        lookup=dict(zip(ids,offsets));k=e&np.isin(g,ids)
        pred=np.array([lookup.get(i,np.nan) for i in g])+x@b
        estimates={}
        for shift in [-2,-1,0,1,2]:
            for diff in [-1,0,1]:
                filled=np.where(o,y,np.clip(pred+shift+diff*c,0,10))
                key=f"{shift:+d}/{diff:+d}"
                try:estimates[key]=fit_arrays(g[k],x[k],filled[k])["beta"]
                except (ValueError,np.linalg.LinAlgError):estimates[key]=None
        return {"scenarios":estimates,"known_exposure_windows":int(k.sum()),
                "interpretation":"Deterministic conditional-mean scenarios, not multiple imputation or confidence intervals"}
    def exposure_shifts():
        # Only valid outcomes; leave missing outcomes unresolved. Impute unknown exposure
        # from a working model fitted to known exposure and observed outcome.
        k=o; observed=e&o
        design=np.column_stack([cov,y])
        if not (~e&o).any():return {"unavailable":"No unknown exposure among valid outcomes"}
        model=probability(design[observed],c[observed])
        p=np.clip(model(design[k]),.001,.999);known=e[k];cc=c[k]
        rng=np.random.default_rng(seed); uniforms=rng.random((draws,k.sum()))
        results={}
        for shift in [-1,0,1]:
            q=expit(logit(p)+shift);values=[]
            for u in uniforms:
                filled=np.where(known,cc,(u<q).astype(float))
                try:values.append(fit_arrays(g[k],np.column_stack([filled,cov[k]]),y[k])["beta"])
                except (ValueError,np.linalg.LinAlgError):continue
            results[str(shift)]={"valid":len(values),"failed":draws-len(values),
                "median":float(np.median(values)) if values else None,
                "scenario_quantiles":np.quantile(values,[.025,.975]).tolist() if values else None}
        return {"draws":draws,"seed":seed,"log_odds_shifts":results,
                "interpretation":"Stochastic exposure scenarios conditional on valid outcome; quantiles are not confidence intervals"}
    if complete.any():
        attempt("stage_ipw",weights)
        attempt("outcome_shifts",outcome_shifts)
        attempt("exposure_shifts",exposure_shifts)
    else:
        for name in ("stage_ipw","outcome_shifts","exposure_shifts"):
            out[name]={"unavailable":"No complete known exposure and outcome windows"}
    return out
