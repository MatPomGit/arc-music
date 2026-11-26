"""Monte Carlo calibration under explicit synthetic mechanisms."""
import argparse
import json
import numpy as np
from scipy.special import expit
from scipy.stats import norm
from inference import design, fit_hc3, contrast, target_weights, impute_pmm, pooled_contrast, composite

def generate(n,delta,mechanism,rng):
    arm=np.arange(n)%2
    rng.shuffle(arm)
    d=rng.uniform(-1.7,1.7,n)
    # Five baseline covariates: expression ease, clarity, distress, experience, scenario.
    c=np.column_stack((rng.uniform(-1,1,(n,3)),rng.integers(0,2,(n,2))-.5))
    x=design(arm,d,c)
    mu=5+.35*x[:,1]-.65*x[:,2]+delta*x[:,3]+c@np.array([.5,.3,-.25,.25,.2])
    if not ((mu>0)&(mu<10)).all():
        raise ValueError("Invalid synthetic mean")
    # Heteroskedastic bounded scores: treatment-specific binomial dispersion;
    # rounding preserves bounded integer outcomes but not an exact conditional mean.
    # Instead use binomial 10 for one arm; mixture of binomial and 0/10 for other.
    p=mu/10
    fit=rng.binomial(10,p).astype(float)
    extreme=(arm==1)&(rng.random(n)<.15)
    fit[extreme]=10*rng.binomial(1,p[extreme])
    meaningful=rng.random(n)>=.10
    y=composite(np.where(meaningful,fit,np.nan),meaningful.astype(float))
    if mechanism=="complete":
        prob=np.zeros(n)
    elif mechanism=="mar":
        prob=expit(-1.55+.6*x[:,1]+.5*x[:,2]+.35*x[:,3]+.25*c[:,0])
    elif mechanism=="mnar":
        prob=expit(-1.55+.6*x[:,1]+.5*x[:,2]+.35*x[:,3]+.25*c[:,0]
                   -.32*(y-4.5)*(1+.5*x[:,1]))
    else:
        raise ValueError("Unknown mechanism")
    # Unknown completion status or applicable missing rating makes the composite missing.
    seen=rng.random(n)>=prob
    return x,np.where(seen,y,np.nan),.90*delta

def wilson(k,n):
    if n==0:
        return None
    p=k/n; z=norm.ppf(.975); d=1+z*z/n
    h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))
    c=p+z*z/(2*n)
    return [(c-h)/d,(c+h)/d]

def scenario(n,delta,mechanism,reps,m,seed):
    rng=np.random.default_rng(seed)
    metrics={name:[] for name in ("complete_outcome","mar")}
    failures={name:0 for name in metrics}
    missing=[]
    for _ in range(reps):
        x,y,truth=generate(n,delta,mechanism,rng)
        w=target_weights(x)
        missing.append(float(np.isnan(y).mean()))
        try:
            b,v,df=fit_hc3(x,y)
            metrics["complete_outcome"].append(contrast(b,v,df,w))
        except (ValueError,np.linalg.LinAlgError):
            failures["complete_outcome"]+=1
        try:
            draws=impute_pmm(x,y,m,int(rng.integers(2**32-1)))
            metrics["mar"].append(pooled_contrast(x,draws,w))
        except (ValueError,np.linalg.LinAlgError):
            failures["mar"]+=1
    out={"n_randomised":n,"latent_fit_interaction":delta,"true_composite_interaction":truth,
         "mechanism":mechanism,"reps_requested":reps,"imputations":m,
         "mean_missing":float(np.mean(missing)),"methods":{}}
    for name,rows in metrics.items():
        valid=len(rows)
        if not valid:
            out["methods"][name]={"valid":0,"failed":failures[name]}
            continue
        est=np.array([v["estimate"] for v in rows])
        bias=est-truth
        cover=sum(v["lower"]<=truth<=v["upper"] for v in rows)
        reject=sum(v["p"]<.05 for v in rows)
        out["methods"][name]={"valid":valid,"failed":failures[name],"bias":float(bias.mean()),
             "bias_mcse":float(bias.std(ddof=1)/np.sqrt(valid)) if valid>1 else None,
             "rmse":float(np.sqrt(np.mean(bias*bias))),
             "coverage":cover/valid,"coverage_mc95":wilson(cover,valid),
             "rejection":reject/valid,"rejection_mc95":wilson(reject,valid)}
    return out

def report(reps=250,m=10,seed=20261126):
    scenarios=[(n,d,mechanism) for n in (480,1000) for d in (0.,.40)
               for mechanism in ("complete","mar","mnar")]
    return {"status":"SYNTHETIC_DESIGN_ONLY","seed":seed,
            "scenarios":[scenario(n,d,mechanism,reps,m,seed+i)
                         for i,(n,d,mechanism) in enumerate(scenarios)]}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--reps",type=int,default=250)
    parser.add_argument("--imputations",type=int,default=10)
    args=parser.parse_args()
    if args.reps<2 or args.imputations<2:
        parser.error("At least two replications and imputations required")
    print(json.dumps(report(args.reps,args.imputations),indent=2,allow_nan=False))
