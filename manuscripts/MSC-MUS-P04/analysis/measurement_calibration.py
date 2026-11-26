"""Synthetic latent vs observed moderator calibration with complete outcomes."""
import argparse
import json
import numpy as np
from scipy.special import expit
from inference import design,fit_hc3,contrast,target_weights
from simulation import wilson
from paq_scoring import score
from reliability import fit_ordinal

NOISE=(.5,.9,1.4)
THRESHOLDS=np.array([-1.5,-.9,-.35,.2,.8,1.4])

def items_from_latent(latent,noise,rng):
    # Same loading, differing hypothetical item thresholds; no actual item text.
    continuous=.8*latent[:,None]+noise*rng.normal(size=(len(latent),6))
    thresholds=THRESHOLDS[None,None,:]+np.linspace(-.2,.2,6)[None,:,None]
    return 1+np.sum(continuous[:,:,None]>thresholds,axis=2)

def population_reference(noise,seed,n=200000):
    rng=np.random.default_rng(seed)
    latent=rng.uniform(-np.sqrt(3),np.sqrt(3),n)
    total=score(items_from_latent(latent,noise,rng))["total"]
    rho=float(np.corrcoef(latent,total)[0,1])
    # Monte Carlo SE via independent blocks; not sampling uncertainty for real PAQ-S.
    blocks=np.array([np.corrcoef(l,t)[0,1] for l,t in zip(np.array_split(latent,20),
                                                         np.array_split(total,20))])
    return {"noise":noise,"n_reference":n,"latent_score_correlation":rho,
            "correlation_mcse":float(blocks.std(ddof=1)/np.sqrt(len(blocks))),
            "score_mean":float(total.mean()),"score_sd":float(total.std(ddof=1))}

def generate(n,delta,noise,rng):
    arm=np.arange(n)%2; rng.shuffle(arm)
    latent=rng.uniform(-np.sqrt(3),np.sqrt(3),n)
    items=items_from_latent(latent,noise,rng)
    total=score(items)["total"]
    cov=np.column_stack((rng.uniform(-1,1,(n,3)),rng.integers(0,2,(n,2))-.5))
    a=arm-.5
    mu=4.2+.25*a-.35*latent+delta*a*latent+cov@np.array([.22,.18,-.15,.12,.1])
    p=.75+.2*expit(.5-.6*latent+.5*a)
    conditional=mu/p/10
    if np.any((conditional<=0)|(conditional>=1)):
        raise ValueError("Invalid bounded mean")
    complete=rng.random(n)<p
    y=complete*rng.binomial(10,conditional)
    return arm,latent,items,total,cov,y

def scenario(n,delta,noise,reference,reps,seed):
    rng=np.random.default_rng(seed)
    rows={"observed":[],"oracle":[]}; failed={k:0 for k in rows}
    truth={"observed":delta*reference["latent_score_correlation"],"oracle":delta}
    for _ in range(reps):
        a,l,items,s,c,y=generate(n,delta,noise,rng)
        for key,d in (("observed",s),("oracle",l)):
            try:
                x=design(a,d,c)
                b,v,df=fit_hc3(x,y)
                q=contrast(b,v,df,target_weights(x))
                rows[key].append((q["estimate"]-truth[key],q["p"]<.05,
                                  q["lower"]<=truth[key]<=q["upper"]))
            except (ValueError,np.linalg.LinAlgError):
                failed[key]+=1
    result={}
    for key,vals in rows.items():
        valid=len(vals)
        if not valid:
            result[key]={"valid":0,"failed":failed[key]}
            continue
        v=np.asarray(vals); reject=int(v[:,1].sum()); cover=int(v[:,2].sum())
        result[key]={"target":truth[key],"valid":valid,"failed":failed[key],
                     "mean_estimate":float(v[:,0].mean()+truth[key]),
                     "bias":float(v[:,0].mean()),
                     "bias_mcse":float(v[:,0].std(ddof=1)/np.sqrt(valid)) if valid>1 else None,
                     "rmse":float(np.sqrt(np.mean(v[:,0]**2))),
                     "rejection":reject/valid,"rejection_mc95":wilson(reject,valid),
                     "coverage":cover/valid,"coverage_mc95":wilson(cover,valid)}
    return {"n_randomised":n,"latent_interaction":delta,"noise":noise,"seed":seed,
            "requested":reps,"methods":result}

def report(reps=300,seed=20261129):
    refs={noise:population_reference(noise,seed+i) for i,noise in enumerate(NOISE)}
    cases=[(n,d,e) for n in (640,1000) for d in (0.,.60) for e in NOISE]
    return {"status":"SYNTHETIC_DESIGN_ONLY","seed":seed,"reference":list(refs.values()),
            "scenarios":[scenario(n,d,e,refs[e],reps,seed+100+i)
                         for i,(n,d,e) in enumerate(cases)]}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--reps",type=int,default=300)
    args=p.parse_args()
    if args.reps<2: p.error("At least two replications required")
    result=report(args.reps)
    print(json.dumps(result,indent=2,allow_nan=False))
    if any(v["failed"] or v["valid"]!=args.reps for s in result["scenarios"] for v in s["methods"].values()):
        raise SystemExit("Synthetic failures; inspect JSON")
