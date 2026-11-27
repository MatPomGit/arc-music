"""Candidate H2/H3 paired synthetic calibration with fixed Holm family.

Bounded integer outcomes have exact linear conditional means in this DGP.
The contrasts are observational within-person projections, not causal effects.
"""
import argparse
import itertools
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import sys
import numpy as np
from scipy.special import expit
from scipy.optimize import brentq
from inference import fit_arrays, holm
from simulation import draw
from stress import selection


def generate(n,prev,effects,mechanism,rng):
    g,x,_,_,_=draw(rng,n,prev,0.,0.,"mar")
    c,v,a,intent,day,hour=x.T
    desired=rng.integers(3,8,len(g))
    dev0=np.abs(a-desired)
    person=rng.uniform(-.45,.45,n)[g]
    # All coefficients refer to the bounded observed-scale conditional mean.
    mu2=5+.20*(v-5)+.06*(a-5)+.06*(intent-5)+.01*(day-11)+.02*(hour-13.5)+person+effects[0]*c
    mu3=1.35+.10*(dev0-2)+.025*(a-5)+.02*(v-5)+.015*(intent-5)+.006*(day-11)+.01*(hour-13.5)+.25*person+effects[1]*c
    if np.any((mu2<=0)|(mu2>=10)|(mu3<=0)|(mu3>=3)):
        raise ValueError("Synthetic bounded mean outside support")
    y2=rng.binomial(10,mu2/10)
    dev=rng.binomial(3,mu3/3)
    arousal=desired+rng.choice([-1,1],len(g))*dev
    y3=np.abs(arousal-desired)
    if not np.all((arousal>=0)&(arousal<=10)):
        raise AssertionError("Invalid synthetic arousal")
    def observed(risk,target=.15):
        intercept=brentq(lambda z:expit(z+risk).mean()-target,-40,40)
        return rng.random(len(g))>=expit(intercept+risk)
    zero=np.zeros(len(g))
    base=observed(zero if mechanism=="mcar" else .18*(v-5))
    ex=observed(zero if mechanism=="mcar" else .20*(intent-5))
    risk2=zero if mechanism=="mcar" else .20*(v-5)+.3*c
    risk3=zero if mechanism=="mcar" else .20*(a-5)+.3*c
    if mechanism=="mnar":
        risk2=risk2+.5*(y2-5)+.25*c*(y2-5)
        risk3=risk3+.6*(y3-1.35)+.35*c*(y3-1.35)
    elif mechanism not in ("mcar","mar"):
        raise ValueError("Unknown mechanism")
    eligible,timely,retained=selection(rng,x,n,21,.45)
    shared=base&ex&eligible&timely&retained
    # H2 does not require the H1 or H3 outcome. Each has its own mask.
    return g,{"H2":(x,y2,shared&observed(risk2)),
              "H3":(np.column_stack([x,dev0]),y3,shared&observed(risk3))}


def attempt(g,x,y,keep):
    try:
        return fit_arrays(g[keep],x[keep],y[keep]),None
    except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
        return None,str(exc)


def rate(k,n):
    if not n:return {"count":int(k),"denominator":int(n),"rate":None,"mcse":None}
    p=k/n
    return {"count":int(k),"denominator":int(n),"rate":float(p),
            "mcse":float(np.sqrt(p*(1-p)/n))}


def scenario_grid(smoke=False):
    grid=list(itertools.product((160,320),(.05,.10,.25),((0.,0.),(.4,0.),(0.,-.2),(.4,-.2)),("mcar","mar","mnar")))
    if smoke:grid=[(160,.05,(0.,0.),"mcar"),(320,.10,(.4,0.),"mar"),
                   (160,.10,(0.,-.2),"mnar"),(320,.25,(.4,-.2),"mar")]
    return grid

def simulate_scenario(task):
    i,(n,prev,effects,mechanism),reps,seed=task
    rng=np.random.default_rng(np.random.SeedSequence([seed,i]))
    keys=("H2","H3"); targets=dict(zip(keys,effects))
    rows={k:[] for k in keys};failures={k:{} for k in keys}
    false_family=joint=any_reject=0
    for _ in range(reps):
        g,models=generate(n,prev,effects,mechanism,rng)
        fits={}
        for key,(x,y,keep) in models.items():
            f,err=attempt(g,x,y,keep)
            if f is None:failures[key][err]=failures[key].get(err,0)+1
            fits[key]=f
        adjusted=holm({k:None if fits[k] is None else fits[k]["p"] for k in keys})
        rejected={k:adjusted[k] is not None and adjusted[k]<=.05 for k in keys}
        false_family+=int(any(rejected[k] and targets[k]==0 for k in keys))
        any_reject+=int(any(rejected.values()))
        joint+=int(all(rejected.values()))
        for k,f in fits.items():
            if f is not None:
                rows[k].append((f["beta"]-targets[k],f["ci"][0]<=targets[k]<=f["ci"][1],rejected[k],f["switchers"]))
    result={}
    for k in keys:
        a=np.asarray(rows[k]);v=len(a)
        reject=int(a[:,2].sum()) if v else 0
        cover=int(a[:,1].sum()) if v else 0
        result[k]={"target":targets[k],"valid":v,"failed":reps-v,"failure_reasons":failures[k],
            "bias":float(a[:,0].mean()) if v else None,
            "bias_mcse":float(a[:,0].std(ddof=1)/np.sqrt(v)) if v>1 else None,
            "coverage_conditional":rate(cover,v),"coverage_operational":rate(cover,reps),
            "holm_rejection_conditional":rate(reject,v),"holm_rejection_operational":rate(reject,reps),
            "mean_switchers":float(a[:,3].mean()) if v else None}
    return {"n":n,"prevalence":prev,"mechanism":mechanism,"targets":targets,
                  "models":result,"any_holm_rejection":rate(any_reject,reps),
                  "joint_holm_rejection":rate(joint,reps),
                  "false_family_rejection":rate(false_family,reps) if 0 in effects else None}

def run(reps=1000,seed=20261205,smoke=False,workers=1,output=None):
    if reps<1 or workers<1 or seed<0:
        raise ValueError("Positive reps/workers and non-negative seed required")
    grid=scenario_grid(smoke)
    tasks=[(i,s,reps,seed) for i,s in enumerate(grid)]
    report={"status":"SYNTHETIC_DEVELOPMENT","seed":seed,"reps":reps,
            "screening_only":smoke or reps<1000,"planned_cells":len(grid),
            "complete":False,"cells":[],
            "interpretation":"Conditional-mean DGP targets; operational failure counts retained. MNAR and selection need not preserve the full eligible projection."}
    if output is not None:
        output=Path(output)
        if output.exists():
            raise FileExistsError("Choose a new output file; existing results are preserved")
        output.parent.mkdir(parents=True,exist_ok=True)
    def save():
        if output is not None:
            tmp=output.with_suffix(output.suffix+".tmp")
            tmp.write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
            tmp.replace(output)
    def record(iterator):
        for result in iterator:
            report["cells"].append(result)
            if output is not None:
                save()
                print(f"{len(report['cells'])}/{len(grid)} scenarios completed",file=sys.stderr,flush=True)
    if workers==1:
        record(map(simulate_scenario,tasks))
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            record(pool.map(simulate_scenario,tasks,chunksize=1))
    report["complete"]=True
    save()
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reps",type=int,default=1000)
    p.add_argument("--seed",type=int,default=20261205)
    p.add_argument("--smoke",action="store_true")
    p.add_argument("--workers",type=int,default=1)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    result=run(a.reps,a.seed,a.smoke,a.workers,a.output)
    if a.output is None:
        print(json.dumps(result,indent=2,allow_nan=False))
