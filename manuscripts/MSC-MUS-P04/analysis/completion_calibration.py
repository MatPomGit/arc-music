"""Completion-aware sensitivity and paired synthetic calibration (no participant data)."""
import argparse
import json
import numpy as np
from scipy.special import expit
from inference import (design, composite, impute_pmm, pooled_contrast, target_weights)
from calibration import robustness
from simulation import wilson

def status_informed_pmm(x, y, status, m=50, seed=20261126, k=5):
    """Known meaningful: impute from meaningful donors; unknown: baseline PMM.
    Known absence must already be a structural zero. Not a general MNAR solution.
    """
    x,y,status=np.asarray(x,float),np.asarray(y,float),np.asarray(status,float)
    if y.shape!=(len(x),) or status.shape!=y.shape:
        raise ValueError("Invalid status dimensions")
    if np.isinf(status).any() or np.any(~np.isin(status[np.isfinite(status)],[0.,1.])):
        raise ValueError("Invalid meaningful-sketch status")
    if np.any((status==0)&(y!=0)) or np.any(np.isnan(status)&np.isfinite(y)):
        raise ValueError("Inconsistent observed outcome and status")
    # Same posterior PMM as primary for participants with unknown status.
    draws=impute_pmm(x,y,m,seed,k)
    meaningful=status==1
    applicable_missing=meaningful&np.isnan(y)
    if applicable_missing.any():
        z=x[meaningful]
        vals=y[meaningful]
        # No restandardisation; the original randomised-sample moderator is retained.
        replacements=impute_pmm(z,vals,m,seed+1,k)
        draws[:,meaningful]=replacements
    return draws

def conditional_means(x,delta):
    """E(Y|X) is linear; E(fit|meaningful,X)=E(Y|X)/P(meaningful|X)."""
    a,d=x[:,1],x[:,2]
    c=x[:,4:]
    prob=.72+.25*expit(.5-.7*d+.8*a+.7*a*d+.25*c[:,0])
    mu=4.2+.25*a-.35*d+delta*x[:,3]+c@np.array([.22,.18,-.15,.12,.1])
    fit_mean=mu/prob
    if np.any((fit_mean<=0)|(fit_mean>=10)):
        raise ValueError("Synthetic conditional mean outside support")
    return prob,mu,fit_mean

def observe(meaningful, fit, answered, status_recorded):
    """Record status when supplied; a meaningful sketch needs an applicable rating."""
    known=answered|status_recorded
    status=np.where(known,meaningful.astype(float),np.nan)
    rating=np.where(answered&meaningful,fit,np.nan)
    return composite(rating,status),status

def generate(n,delta,mechanism,rng):
    a=np.arange(n)%2
    rng.shuffle(a)
    d=rng.integers(4,29,n)
    # Correlated baseline measures, bounded continuous covariates and binary covariates.
    t=(d-16)/12
    c=np.column_stack((np.clip(-.55*t+rng.uniform(-.6,.6,n),-1,1),
                       np.clip(-.45*t+rng.uniform(-.7,.7,n),-1,1),
                       np.clip(.45*t+rng.uniform(-.7,.7,n),-1,1),
                       rng.binomial(1,expit(.2-.5*t))-.5,
                       rng.binomial(1,expit(-.2+.4*t))-.5))
    x=design(a,d,c)
    prob,mu,fit_mean=conditional_means(x,delta)
    meaningful=rng.random(n)<prob
    fit=rng.binomial(10,fit_mean/10).astype(float)
    extreme=(a==1)&(rng.random(n)<.12)
    fit[extreme]=10*rng.binomial(1,fit_mean[extreme]/10)
    # Nonresponse depends on status; outcome-dependent adds unobserved applicable fit.
    logit=-1.8+.35*x[:,1]+.45*x[:,2]+.35*x[:,3]+1.0*(~meaningful)
    if mechanism=="outcome_dependent":
        logit+=np.where(meaningful,-.35*(fit-fit_mean)*(1+.5*x[:,1]),0.)
    elif mechanism!="status_dependent":
        raise ValueError("Unknown missingness mechanism")
    answered=rng.random(n)>=expit(logit)
    # Paired hypothetical data collection: same people, rating response and uniforms.
    # Status availability among nonresponders can itself depend on true status.
    u=rng.random(n)
    basic=u<np.where(meaningful,.45,.25)
    enhanced=u<np.where(meaningful,.90,.85)
    low=observe(meaningful,fit,answered,basic)
    high=observe(meaningful,fit,answered,enhanced)
    return x,low,high,meaningful,mu

def summarize(rows,failed,reps):
    n=len(rows)
    if n==0:
        return {"requested":reps,"valid":0,"failed":failed}
    arr=np.array(rows)
    out={"requested":reps,"valid":n,"failed":failed,
         "bias":float(arr[:,0].mean()),"bias_mcse":float(arr[:,0].std(ddof=1)/np.sqrt(n)) if n>1 else None,
         "rmse":float(np.sqrt(np.mean(arr[:,0]**2))),
         "mean_missing_outcome":float(arr[:,4].mean()),"mean_missing_status":float(arr[:,5].mean()),
         "mean_structural_zero_observed":float(arr[:,6].mean())}
    for name,i in (("nominal_rejection",1),("coverage",2),("grid_robust_rejection",3)):
        k=int(arr[:,i].sum())
        out[name]=k/n
        out[name+"_mc95"]=wilson(k,n)
    return out

METHODS=("baseline_pmm","status_informed","enhanced_status_informed")

def scenario(n,delta,mechanism,reps,m,seed):
    rng=np.random.default_rng(seed)
    rows={name:[] for name in METHODS}
    failed={name:0 for name in METHODS}
    differences=[]
    completion=[]
    for _ in range(reps):
        x,low,high,meaningful,mu=generate(n,delta,mechanism,rng)
        w=target_weights(x)
        # Truth is exactly delta for each generated baseline design, not a noisy fitted outcome.
        truth=float(np.linalg.lstsq(x,mu,rcond=None)[0][3])
        if not np.isclose(truth,delta,atol=1e-10):
            raise RuntimeError("Synthetic estimand mismatch")
        completion.append([float(meaningful[x[:,1]==a].mean()) for a in (-.5,.5)])
        draw_seed=int(rng.integers(2**32-1))
        paired={}
        for name,(y,status) in zip(METHODS,(low,low,high)):
            try:
                draws=(impute_pmm(x,y,m,draw_seed) if name==METHODS[0]
                       else status_informed_pmm(x,y,status,m,draw_seed))
                q=pooled_contrast(x,draws,w)
                row=(q["estimate"]-truth,q["p"]<.05,q["lower"]<=truth<=q["upper"],
                     robustness(x,y,draws,w,q),np.isnan(y).mean(),np.isnan(status).mean(),
                     (status==0).mean())
                rows[name].append(row)
                paired[name]=row
            except (ValueError,np.linalg.LinAlgError):
                failed[name]+=1
        if len(paired)==len(METHODS):
            differences.append([float(paired[method][j])-float(paired[METHODS[0]][j])
                                for method in METHODS[1:] for j in (0,1,2,3,4)])
    pair=np.asarray(differences)
    labels=[method+"_"+metric for method in METHODS[1:]
            for metric in ("bias","nominal_rejection","coverage","robust_rejection","missing_outcome")]
    summary={}
    if len(pair)>1:
        for i,key in enumerate(labels):
            summary[key]={"mean_difference":float(pair[:,i].mean()),
                          "paired_mcse":float(pair[:,i].std(ddof=1)/np.sqrt(len(pair)))}
    return {"n_randomised":n,"true_composite_interaction":delta,"mechanism":mechanism,
            "seed":seed,"imputations":m,"mean_true_completion_by_arm":np.mean(completion,axis=0).tolist(),
            "methods":{name:summarize(rows[name],failed[name],reps) for name in METHODS},
            "paired_valid":len(pair),"paired_differences_vs_baseline":summary}

def report(reps=120,m=50,seed=20261128):
    cases=[(1000,d,mech) for mech in ("status_dependent","outcome_dependent") for d in (0.,.54,.72)]
    return {"status":"SYNTHETIC_DESIGN_ONLY","seed":seed,"scenarios":[
        scenario(n,d,mech,reps,m,seed+i) for i,(n,d,mech) in enumerate(cases)]}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--reps",type=int,default=120)
    p.add_argument("--imputations",type=int,default=50)
    args=p.parse_args()
    if min(args.reps,args.imputations)<2:
        p.error("At least two replications and imputations required")
    result=report(args.reps,args.imputations)
    print(json.dumps(result,indent=2,allow_nan=False))
    if any(v["failed"] or v["valid"]!=args.reps for s in result["scenarios"] for v in s["methods"].values()):
        raise SystemExit("Calibration failures; inspect JSON")
