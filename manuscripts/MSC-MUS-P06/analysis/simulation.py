"""Synthetic design sensitivity; not empirical outcomes or final sample size."""
import argparse
import json
import itertools
import numpy as np
from scipy.special import expit
from scipy.optimize import brentq
from inference import fit_arrays

def draw(rng,n,m,beta,missing=.15,rho=.4,slope_sd=.2,scenario="mar"):
    if not (0 <= missing < 1 and 0 <= rho < 1 and n >= 10 and 2 <= m <= 14):
        raise ValueError("Invalid design parameters")
    g=np.repeat(np.arange(n),m)
    day=np.tile(np.arange(1,m+1),n)
    mood=np.repeat(rng.normal(0,1,n),m)
    a=np.clip(np.round(5+.5*mood+rng.normal(0,2,n*m)),0,10)
    d=np.clip(np.round(5+.4*mood+rng.normal(0,1.8,n*m)),0,10)
    k=np.clip(np.round(5+rng.normal(0,2,n*m)),0,10)
    u=rng.normal(0,1.0,n)
    random_slope=rng.normal(0,slope_sd,n)
    noise=rng.normal(0,1.5,(n,m))
    for j in range(1,m):
        noise[:,j]=rho*noise[:,j-1]+np.sqrt(1-rho**2)*noise[:,j]
    # Continuous outcome preserves a known conditional data-generating slope.
    # Bounded ratings require separate calibration against the observed-scale target.
    y=5+u[g]+(beta+random_slope[g])*(a-5)+.2*(d-5)+.15*(k-5)+.02*day+noise.ravel()
    if scenario not in ("mcar","mar","mnar"):
        raise ValueError("Unknown missingness mechanism")
    score=np.zeros(n*m) if scenario=="mcar" else .25*(d-5)+.1*(a-5)
    if scenario=="mnar":
        score=score+.35*(y-5)
    if missing==0:
        keep=np.ones(n*m,dtype=bool)
    else:
        intercept=brentq(lambda z:expit(z+score).mean()-missing,-40,40)
        keep=rng.random(n*m)>=expit(intercept+score)
    x=np.column_stack([a,d,k,day])
    return g[keep],x[keep],y[keep]

def run_cell(rng,n,m,beta,missing,scenario,reps):
    estimates=[]; rejected=[]; covered=[]; failures=0; observed=[]
    for _ in range(reps):
        try:
            r=fit_arrays(*draw(rng,n,m,beta,missing,scenario=scenario))
        except (ValueError,np.linalg.LinAlgError):
            failures+=1
            continue
        estimates.append(r["estimate"][0])
        rejected.append(r["p"][0]<.05)
        covered.append(r["ci_low"][0]<=beta<=r["ci_high"][0])
        observed.append(r["sessions"])
    valid=len(estimates)
    rate=lambda x:float(np.mean(x)) if valid else None
    reject=rate(rejected)
    return dict(n=n,sessions_per_person=m,beta=beta,missing=missing,
                scenario=scenario,reps=reps,valid=valid,failures=failures,
                rejection_rate=reject,mcse_rejection=float(np.sqrt(reject*(1-reject)/valid)) if valid else None,
                coverage=rate(covered),bias=float(np.mean(estimates)-beta) if valid else None,
                mean_observed_sessions=rate(observed))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--reps",type=int,default=1000)
    p.add_argument("--seed",type=int,default=2606)
    p.add_argument("--smoke",action="store_true")
    args=p.parse_args()
    if args.reps<1:
        p.error("reps must be positive")
    grid=itertools.product([80,160] if args.smoke else [80,120,160,240],
                           [6] if args.smoke else [4,6,10],
                           [0,.30] if args.smoke else [0,.15,.30,.45],
                           [.30] if args.smoke else [.15,.30,.45],
                           ["mar"] if args.smoke else ["mcar","mar","mnar"])
    rng=np.random.default_rng(args.seed)
    cells=[run_cell(rng,*cell,args.reps) for cell in grid]
    print(json.dumps({"status":"SYNTHETIC_CONTINUOUS_OUTCOME",
                      "seed":args.seed,"cells":cells},indent=2,allow_nan=False))
if __name__=="__main__":
    main()
