"""Paired synthetic measurement-error x missingness calibration for P04.

The population linear projection uses an observed standardized six-item sum.
Oracle latent effects are not the empirical estimand. No clinical data.
"""
import argparse
import itertools
import json
import numpy as np
from scipy.special import expit
from inference import (design,composite,impute_pmm,pooled_contrast,target_weights,
                       shift_imputed,robustness_label)
from completion_calibration import status_informed_pmm, observe
from measurement_calibration import items_from_latent,population_reference,NOISE
from paq_scoring import score
from simulation import wilson


def generate(n,delta,noise,mechanism,rng):
    a=np.arange(n)%2; rng.shuffle(a)
    latent=rng.uniform(-np.sqrt(3),np.sqrt(3),n)
    total=score(items_from_latent(latent,noise,rng))["total"]
    cov=np.column_stack((rng.uniform(-1,1,(n,3)),rng.integers(0,2,(n,2))-.5))
    x=design(a,total,cov)
    z=a-.5
    mu=4.2+.25*z-.35*latent+delta*z*latent+cov@np.array([.22,.18,-.15,.12,.1])
    prob=.75+.2*expit(.5-.6*latent+.5*z)
    conditional=mu/prob/10
    if np.any((conditional<=0)|(conditional>=1)):
        raise ValueError("Synthetic mean outside bounds")
    meaningful=rng.random(n)<prob
    fit=rng.binomial(10,conditional).astype(float)
    logit=-1.8+.35*x[:,1]+.45*x[:,2]+.35*x[:,3]
    if mechanism in ("status_dependent","outcome_dependent"):
        logit+=1.*(~meaningful)
    if mechanism=="outcome_dependent":
        logit+=np.where(meaningful,-.35*(fit-mu/prob)*(1+.5*x[:,1]),0.)
    elif mechanism not in ("baseline_mar","status_dependent","composite_mar"):
        raise ValueError("Unknown mechanism")
    answered=rng.random(n)>=expit(logit)
    u=rng.random(n)
    if mechanism=="composite_mar":
        # Composite response depends only on observed baseline X. No separate
        # status ascertainment of nonresponders can reveal structural zeros.
        low=observe(meaningful,fit,answered,np.zeros(n,dtype=bool))
        return x,low,(low[0].copy(),low[1].copy())
    low=observe(meaningful,fit,answered,u<np.where(meaningful,.45,.25))
    high=observe(meaningful,fit,answered,u<np.where(meaningful,.90,.85))
    return x,low,high


def estimate(x,y,status,m,seed,method,grid=True):
    w=target_weights(x)
    draws=(impute_pmm(x,y,m,seed) if method=="baseline_pmm"
           else status_informed_pmm(x,y,status,m,seed))
    q=pooled_contrast(x,draws,w)
    result={"mar":q}
    if grid:
        s=[{"offset_control":i,"offset_scaffold":j,"differential_slope":k,
            **pooled_contrast(x,shift_imputed(x,y,draws,i,j,k),w)}
           for i in (-2,0,2) for j in (-2,0,2) for k in (-1,0,1)]
        result.update(sensitivity=s,robustness_label=robustness_label(q,s))
    return result


def proportion(k,n):
    k,n=int(k),int(n)
    if not n:
        return {"count":k,"denominator":n,"rate":None,"mcse":None,"mc95":None}
    p=k/n
    return {"count":k,"denominator":n,"rate":p,"mcse":float(np.sqrt(p*(1-p)/n)),
            "mc95":wilson(k,n)}


def summarize(rows,failures,reps,truth):
    v=len(rows)
    errors=np.asarray([r["mar"]["estimate"]-truth for r in rows])
    reject=sum(r["mar"]["p"]<.05 for r in rows)
    cover=sum(r["mar"]["lower"]<=truth<=r["mar"]["upper"] for r in rows)
    robust=sum(r.get("robustness_label","").startswith("ROBUST_") for r in rows)
    return {"requested":reps,"valid":v,"failed":reps-v,"failure_reasons":failures,
            "bias":float(errors.mean()) if v else None,
            "bias_mcse":float(errors.std(ddof=1)/np.sqrt(v)) if v>1 else None,
            "rmse":float(np.sqrt((errors**2).mean())) if v else None,
            "nominal_rejection_conditional":proportion(reject,v),
            "nominal_rejection_operational":proportion(reject,reps),
            "coverage_conditional":proportion(cover,v),"coverage_operational":proportion(cover,reps),
            "grid_robust_conditional":proportion(robust,v),
            "grid_robust_operational":proportion(robust,reps)}


def run(reps=20,m=50,seed=20261204,smoke=False,*,include_composite_mar=False, design=None):
    if reps<2 or m<2:
        raise ValueError("At least two independent datasets and imputations")
    grid=list(itertools.product((660,1000),(0.,.60),NOISE,
                                ("baseline_mar","status_dependent","outcome_dependent")))
    if smoke:
        grid=[(660,0.,.9,"baseline_mar"),(1000,.60,1.4,"outcome_dependent")]
    if include_composite_mar:
        extra=[(660,0.,.9,"composite_mar")] if smoke else list(itertools.product((660,1000),(0.,.60),NOISE,("composite_mar",)))
        grid+=extra
    if design is not None:
        n,delta,noise,mechanism=design
        if n<100 or n%2 or not -.6<=delta<=.6 or noise not in NOISE or mechanism not in ('baseline_mar','status_dependent','outcome_dependent','composite_mar'):
            raise ValueError('Invalid custom design')
        grid=[design]
    refs={noise:population_reference(noise,seed+100+i,n=200000) for i,noise in enumerate(NOISE)}
    cells=[]
    for i,(n,delta,noise,mechanism) in enumerate(grid):
        rng=np.random.default_rng(np.random.SeedSequence([seed,i]))
        truth=delta*refs[noise]["latent_score_correlation"]
        methods=("baseline_pmm","status_informed","enhanced_status_informed")
        rows={k:[] for k in methods}; failures={k:{} for k in methods}
        for j in range(reps):
            x,low,high=generate(n,delta,noise,mechanism,rng)
            draw_seed=int(rng.integers(2**32-1))
            for method,(y,status) in zip(methods,(low,low,high)):
                try:
                    rows[method].append(estimate(x,y,status,m,draw_seed,method))
                except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
                    key=str(exc)
                    failures[method][key]=failures[method].get(key,0)+1
        cells.append({"n":n,"latent_interaction":delta,"noise":noise,"mechanism":mechanism,
                      "mechanism_scope":("pure composite MAR; no separate status capture" if mechanism=="composite_mar" else
                          "baseline-only rating response; composite observation also depends on status capture" if mechanism=="baseline_mar" else
                          "status- or outcome-dependent rating response and status capture"),
                      "mean_capture_is_not_a_causal_effect":True,
                      "observed_target":truth,"reference_correlation_mcse":refs[noise]["correlation_mcse"],
                      "methods":{k:summarize(rows[k],failures[k],reps,truth) for k in methods}})
    return {"status":"SYNTHETIC_DEVELOPMENT","seed":seed,"reps":reps,"m":m,
            "reference":list(refs.values()),"cells":cells,"confirmatory_authorized":False}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reps",type=int,default=20)
    p.add_argument("--m",type=int,default=50)
    p.add_argument("--seed",type=int,default=20261204)
    p.add_argument("--smoke",action="store_true")
    p.add_argument("--include-composite-mar",action="store_true",help="Append pure composite-MAR reference without changing the historical grid order")
    p.add_argument('--design',nargs=4)
    a=p.parse_args()
    design=None if a.design is None else (int(a.design[0]),float(a.design[1]),float(a.design[2]),a.design[3])
    print(json.dumps(run(a.reps,a.m,a.seed,a.smoke,include_composite_mar=a.include_composite_mar,design=design),indent=2,allow_nan=False))
