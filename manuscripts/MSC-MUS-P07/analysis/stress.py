"""Rare creation, ongoing windows, timing loss and monotone withdrawal calibration."""
import argparse,json,platform
from itertools import product
import numpy as np
import scipy
from scipy.special import expit
from scipy.optimize import brentq
from inference import fit_arrays
from simulation import draw

def calibrate_probability(risk,target):
    if target==0:return np.zeros_like(risk,dtype=float)
    if not 0<target<1:raise ValueError("Invalid probability target")
    z=brentq(lambda z:expit(z+risk).mean()-target,-40,40)
    return expit(z+risk)

def selection(rng,x,n,days,dropout,ongoing=.15,timing=.10):
    if len(x)!=n*days:raise ValueError("Invalid window count")
    # Ongoing activity is a distinct eligibility exclusion, not missing exposure.
    # Shared intention predicts the probability of ongoing creation.
    q=calibrate_probability(.3*(x[:,3]-4),ongoing)
    eligible=rng.random(len(x))>=q
    timely=rng.random(len(x))>=timing
    retained=np.ones((n,days),dtype=bool)
    if dropout:
        # Informative monotone loss: previous day's latent baseline valence
        # and intention can be unavailable in the actual observed ledger.
        # This is not guaranteed MAR relative to the available data.
        risk=.15*(5-x[:,1].reshape(n,days)[:,:-1])-.12*(x[:,3].reshape(n,days)[:,:-1]-4)
        z=brentq(lambda z:np.mean(1-np.prod(1-expit(z+risk),axis=1))-dropout,-40,40)
        retained[:,1:]=np.cumprod(rng.random((n,days-1))>=expit(z+risk),axis=1).astype(bool)
    return eligible,timely,retained.ravel()

def scenarios(n):
    if n not in (160,320):raise ValueError("Prespecified n required")
    return list(product([.05,.10,.25],[0.,.4],[.15,.45]))

def run(n=160,reps=1000,reference_n=20000,seed=2709):
    if reps<1 or reference_n<100:raise ValueError("Invalid calibration size")
    rng=np.random.default_rng(seed+n);refs={};cells=[]
    for prev,beta,drop in scenarios(n):
        key=(prev,beta)
        if key not in refs:
            g,x,y,_,_=draw(rng,reference_n,prev,beta,0,"mar",rho=.4)
            eligible,_,_=selection(rng,x,reference_n,21,0,timing=0)
            refs[key]=fit_arrays(g[eligible],x[eligible],y[eligible])
        ref=refs[key];target=ref["beta"]
        fits=[];flows=[];failures=0
        for _ in range(reps):
            g,x,y,stage,_=draw(rng,n,prev,beta,.30,"mar",rho=.4)
            eligible,timely,retained=selection(rng,x,n,21,drop)
            keep=eligible&timely&retained&stage
            exposed=np.bincount(g[keep],weights=x[keep,0],minlength=n)
            count=np.bincount(g[keep],minlength=n)
            switches=(exposed>0)&(exposed<count)
            flows.append((eligible.mean(),retained.reshape(n,21)[:,-1].mean(),keep.mean(),
                          switches.sum(),x[keep,0].mean() if keep.any() else np.nan))
            try:
                f=fit_arrays(g[keep],x[keep],y[keep])
                fits.append((f["beta"],f["ci"][0]<=target<=f["ci"][1],f["p"]<.05))
            except (ValueError,np.linalg.LinAlgError):failures+=1
        a=np.array(fits);v=len(a);flow=np.array(flows)
        def mean(j):return float(a[:,j].mean()) if v else None
        r=mean(2);c=mean(1)
        cells.append(dict(n=n,prevalence=prev,latent_beta=beta,final_dropout=drop,
                          reference_beta=target,reference_se=ref["se"],valid=v,failures=failures,
                          valid_fraction=v/reps,mean_beta=mean(0),bias=mean(0)-target if v else None,
                          rejection_zero=r,coverage_reference=c,
                          unconditional_rejection=sum(a[:,2])/reps if v else 0.,
                          rejection_mcse=float(np.sqrt(r*(1-r)/v)) if v else None,
                          coverage_mcse=float(np.sqrt(c*(1-c)/v)) if v else None,
                          mean_eligible_fraction=float(flow[:,0].mean()),
                          mean_final_retention=float(flow[:,1].mean()),
                          mean_complete_fraction=float(flow[:,2].mean()),
                          mean_switchers=float(flow[:,3].mean()),
                          switcher_q05=float(np.quantile(flow[:,3],.05)),
                          probability_50_switchers=float(np.mean(flow[:,3]>=50)),
                          mean_observed_creation=float(np.nanmean(flow[:,4])) if np.isfinite(flow[:,4]).any() else None))
    return dict(status="SYNTHETIC_STRESS",seed=seed+n,reps=reps,reference_n=reference_n,
                n=n,screening_only=reps<1000,days=21,stage_loss=.30,ongoing=.15,timing_loss=.10,
                rho=.4,environment={"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__},
                cells=cells)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--n",type=int,choices=[160,320],default=160)
    p.add_argument("--reps",type=int,default=1000)
    p.add_argument("--reference-n",type=int,default=20000)
    p.add_argument("--seed",type=int,default=2709)
    a=p.parse_args()
    print(json.dumps(run(a.n,a.reps,a.reference_n,a.seed),indent=2,allow_nan=False))
