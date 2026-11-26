"""Synthetic bounded EMA design calibration, using the production estimator."""
import argparse,json
from itertools import product
import numpy as np
from scipy.special import expit
from scipy.optimize import brentq
from inference import fit_arrays

def draw(rng,n,prevalence,beta,missing,mechanism,days=21,rho=.4):
    if not (0<prevalence<1 and 0<=missing<1 and 0<=rho<1):raise ValueError("Invalid design parameters")
    if mechanism not in ("mcar","mar","mnar","confounded"):raise ValueError("Unknown mechanism")
    g=np.repeat(np.arange(n),days);day=np.tile(np.arange(1,days+1),n)
    u=rng.normal(size=n); propensity=rng.normal(0,1.15,n)
    hour=rng.uniform(9,18,len(g))
    v=np.clip(np.rint(5+.7*u[g]+rng.normal(0,1.7,len(g))),0,10)
    a=np.clip(np.rint(5+rng.normal(0,1.8,len(g))),0,10)
    intention=np.clip(np.rint(4+.9*propensity[g]+rng.normal(0,2,len(g))),0,10)
    unmeasured=rng.normal(size=len(g))
    logits=propensity[g]+.25*(intention-4)-.15*(v-5)+.07*(hour-13.5)
    if mechanism=="confounded":logits+=.7*unmeasured
    intercept=brentq(lambda z:expit(z+logits).mean()-prevalence,-40,40)
    c=(rng.random(len(g))<expit(intercept+logits)).astype(int)
    e=rng.normal(0,1.5,(n,days))
    for j in range(1,days):e[:,j]=rho*e[:,j-1]+np.sqrt(1-rho*rho)*e[:,j]
    slopes=rng.normal(beta,.25,n)
    y=5+.7*u[g]+.35*(v-5)+.12*(a-5)+.08*(intention-4)+.015*(day-11)+.04*(hour-13.5)+slopes[g]*c+e.ravel()
    if mechanism=="confounded":y+=.65*unmeasured
    y=np.clip(np.rint(y),0,10)
    x=np.column_stack([c,v,a,intention,day,hour])
    # Distinct stages: missed baseline, unreported exposure, missing outcome.
    # Rates calibrated to combined expected complete-window loss under MCAR;
    # under MAR/MNAR calibrated conditional stage mean, realized loss may differ.
    stage=1-(1-missing)**(1/3)
    def observed(risk):
        if stage==0:return np.ones(len(g),dtype=bool)
        z=brentq(lambda z:expit(z+risk).mean()-stage,-40,40)
        return rng.random(len(g))>=expit(z+risk)
    zero=np.zeros(len(g))
    b=observed(zero if mechanism=="mcar" else .18*(v-5))
    exposure=observed(zero if mechanism=="mcar" else .20*(intention-4)+(.9*c if mechanism=="mnar" else 0))
    outcome=observed(zero if mechanism=="mcar" else .20*(v-5)+.3*c+(.55*(y-5)+.25*c*(y-5) if mechanism=="mnar" else 0))
    keep=b&exposure&outcome
    return g,x,y,keep,{"baseline":float(b.mean()),"exposure_given_baseline":float(exposure[b].mean()) if b.any() else 0.,
                       "complete":float(keep.mean()),"prevalence":float(c.mean())}

def scenarios(smoke=False):
    if smoke:return [(80,.10,0.,.30,"mar"),(80,.25,.4,.30,"mnar"),(160,.25,.4,.30,"mar")]
    core=list(product([80,160,320],[.10,.25,.40],[0.,.4],[.30],["mar"]))
    stress=list(product([160],[.10,.25],[0.,.2,.6],[.15,.45],["mcar","mnar"]))
    return core+stress+[(160,.25,0.,.30,"confounded"),(160,.25,.4,.30,"confounded")]

def run(reps=200,reference_n=10000,seed=2707,smoke=False):
    if reps<1 or reference_n<100:raise ValueError("Invalid calibration size")
    rng=np.random.default_rng(seed); references={};cells=[]
    for n,prev,beta,missing,mechanism in scenarios(smoke):
        key=(prev,beta,mechanism=="confounded")
        if key not in references:
            g,x,y,_,_=draw(rng,reference_n,prev,beta,0,"confounded" if key[2] else "mar")
            references[key]=fit_arrays(g,x,y)
        target=references[key]["beta"]
        records=[];failed=0
        for _ in range(reps):
            g,x,y,keep,flow=draw(rng,n,prev,beta,missing,mechanism)
            try:
                f=fit_arrays(g[keep],x[keep],y[keep])
                records.append((f["beta"],f["ci"][0]<=target<=f["ci"][1],f["p"]<.05,
                                f["switchers"],f["windows"],flow["complete"]))
            except (ValueError,np.linalg.LinAlgError):failed+=1
        a=np.asarray(records);v=len(a)
        def fraction(col):return float(a[:,col].mean()) if v else None
        rejection=fraction(2);coverage=fraction(1)
        cells.append(dict(n=n,prevalence=prev,latent_beta=beta,missing=missing,mechanism=mechanism,
                          reference_beta=target,reference_se=references[key]["se"],valid=v,failures=failed,
                          valid_fraction=v/reps,mean_beta=fraction(0),bias=fraction(0)-target if v else None,
                          coverage_reference=coverage,rejection_zero=rejection,
                          rejection_mcse=float(np.sqrt(rejection*(1-rejection)/v)) if v else None,
                          coverage_mcse=float(np.sqrt(coverage*(1-coverage)/v)) if v else None,
                          mean_switchers=fraction(3),mean_windows=fraction(4),mean_complete_fraction=fraction(5)))
    return dict(status="SYNTHETIC",seed=seed,reps=reps,reference_n=reference_n,smoke=smoke,
                screening_only=smoke or reps<1000,cells=cells)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--reps",type=int,default=200)
    p.add_argument("--reference-n",type=int,default=10000);p.add_argument("--seed",type=int,default=2707)
    p.add_argument("--smoke",action="store_true");a=p.parse_args()
    print(json.dumps(run(a.reps,a.reference_n,a.seed,a.smoke),indent=2,allow_nan=False))
