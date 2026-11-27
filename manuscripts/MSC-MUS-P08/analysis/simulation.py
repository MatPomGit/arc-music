"""Synthetic power calibration of bounded P08 composites and factorial contrasts."""
import argparse,json,platform
from itertools import product
import numpy as np
import scipy
from scipy.special import expit
from scipy.optimize import brentq
from inference import fit_arrays,holm

def draw(rng,n,authority,interaction,mechanism,loss=.20,nonadherence=0.):
    if n%4 or n<16:raise ValueError("n must be a multiple of four")
    if mechanism not in ("mcar","mar","mnar") or not (0<=loss<1 and 0<=nonadherence<1):raise ValueError("Invalid missingness")
    # Exact balanced allocation; training balance is not forced in this approximation.
    a,e=np.tile(np.array([[-.5,-.5],[-.5,.5],[.5,-.5],[.5,.5]]),(n//4,1)).T
    training=rng.binomial(1,.35,n)
    prior=np.minimum(rng.poisson(5+3*training),30)
    familiarity=np.clip(np.rint(3+.25*prior+rng.normal(0,1.8,n)),0,10)
    anticipated=np.clip(np.rint(5+.3*training+rng.normal(0,1.7,n)),0,10)
    b=np.column_stack([training,prior,familiarity,anticipated])
    x=np.column_stack([np.ones(n),a,e,a*e,b-b.mean(axis=0)])
    # An interruption can suppress an assigned feature. Never recode assignment
    # or exclude its participant. This simulates treatment dilution, not crossover.
    applied_a, applied_e = a, e
    if nonadherence:
        applied_a = np.where((a > 0) & (rng.random(n) < nonadherence), -.5, a)
        applied_e = np.where((e > 0) & (rng.random(n) < nonadherence), -.5, e)
    shared=rng.normal(size=n)
    # Both outcomes share subject variance but have separate item errors.
    # Heteroskedasticity varies by execution (not authority), avoiding a
    # mechanical authority null violation in the symmetric generating model.
    sd=1.25+.35*(applied_e+.5)
    mu=5+authority*applied_a+.20*applied_e+interaction*applied_a*applied_e+.18*(anticipated-5)+.08*(familiarity-5)
    ag=5+authority*applied_a+.10*applied_e+.12*(anticipated-5)+.12*(familiarity-5)
    y=[]; masks=[]
    for j,m in enumerate([mu,ag]):
        latent=m+sd*(.55*shared+np.sqrt(1-.55**2)*rng.normal(size=n))
        items=np.clip(np.rint(latent[:,None]+rng.normal(0,.65,(n,3))),0,10)
        value=items.mean(axis=1)
        risk=np.zeros(n) if mechanism=="mcar" else .25*(anticipated-5)-.15*(familiarity-5)+.35*a-.20*e
        if mechanism=="mnar":risk=risk+.45*(value-5)+.6*a*(value-5)
        if loss:
            z=brentq(lambda z:expit(z+risk).mean()-loss,-40,40)
            observed=rng.random(n)>=expit(z+risk)
        else:observed=np.ones(n,dtype=bool)
        y.append(value);masks.append(observed)
    return x,y,masks

def scenarios(smoke=False):
    if smoke:return [(240,0.,0.,"mcar"),(480,.45,.6,"mnar")]
    return list(product([240,480,720],[0.,.45],[0.,.6],["mcar","mar","mnar"]))

def contrasts(x,y,masks):
    out = []
    for v, k in zip(y, masks):
        try:
            out.append(fit_arrays(x[k], v[k]))
        except (ValueError, np.linalg.LinAlgError):
            out.append({})
    return {"H1": out[0].get("authority"), "H2": out[1].get("authority"),
            "H3": out[0].get("interaction")}

def run(reps=500,reference_n=40000,seed=2808,smoke=False,nonadherence=0., *, grid=None, loss=.20):
    if reps<1 or reference_n<100 or reference_n%4 or not 0<=loss<1:raise ValueError("Invalid calibration size")
    rng=np.random.default_rng(seed); refs={};cells=[]
    for n,a,interaction,mechanism in (scenarios(smoke) if grid is None else grid):
        key=(a,interaction)
        if key not in refs:
            x,y,k=draw(rng,reference_n,a,interaction,"mcar",loss=0,nonadherence=nonadherence)
            refs[key]=contrasts(x,y,k)
        ref=refs[key];stats={h:[] for h in ref};joint=0;failed=0
        for _ in range(reps):
            x,y,k=draw(rng,n,a,interaction,mechanism,loss=loss,nonadherence=nonadherence)
            f = contrasts(x, y, k)
            failed += int(any(value is None for value in f.values()))
            adj = holm({h: f[h]["p"] if f[h] else None for h in ("H2", "H3")})
            reject = {"H1": bool(f["H1"] and f["H1"]["p"] < .05),
                      **{h: value is not None and value < .05 for h, value in adj.items()}}
            joint+=int(all(reject.values()))
            for h,v in f.items():
                if v is None:
                    continue
                target = 0. if (a == interaction == 0 or (h == "H2" and a == 0)) else ref[h]["beta"]
                stats[h].append((v["beta"],v["ci"][0]<=target<=v["ci"][1],reject[h],
                                 float(k[1 if h=="H2" else 0].mean())))
        results={}
        for h,s in stats.items():
            z=np.asarray(s);valid=len(z)
            exact_null = a == interaction == 0 or (h == "H2" and a == 0)
            target = 0. if exact_null else ref[h]["beta"]
            def avg(i):return float(z[:,i].mean()) if valid else None
            r=avg(2);c=avg(1)
            results[h]=dict(reference=target,reference_se=ref[h]["se"],mean_beta=avg(0),
              bias=avg(0)-target if valid else None,coverage_reference=c,
              rmse=float(np.sqrt(np.mean((z[:,0]-target)**2))) if valid else None,
              exact_null=exact_null, valid=valid, failures=reps-valid,
              rejection_kind="type_i" if exact_null else "rejection_against_zero",
              unconditional_rejection_mcse=float(np.sqrt(
                  (z[:,2].sum()/reps)*(1-z[:,2].sum()/reps)/reps)) if valid else 0.,
              rejection=r,unconditional_rejection=float(z[:,2].sum()/reps) if valid else 0.,
              rejection_mcse=float(np.sqrt(r*(1-r)/valid)) if valid else None,
              coverage_mcse=float(np.sqrt(c*(1-c)/valid)) if valid else None,
              observed_fraction=avg(3))
        cells.append(dict(n=n,latent_authority=a,latent_interaction=interaction,mechanism=mechanism,
          valid=reps-failed,failures=failed,all_three_reject=joint/reps,contrasts=results))
    return dict(status="SYNTHETIC",seed=seed,reps=reps,reference_n=reference_n,screening_only=smoke or reps<1000,
      nonadherence=nonadherence,expected_missingness=loss,environment={"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__},cells=cells)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--reps",type=int,default=500)
    p.add_argument("--reference-n",type=int,default=40000);p.add_argument("--seed",type=int,default=2808)
    p.add_argument("--smoke",action="store_true")
    p.add_argument("--nonadherence",type=float,default=0.)
    p.add_argument('--design',nargs=4)
    p.add_argument('--loss',type=float,default=.20)
    a=p.parse_args()
    grid=None if a.design is None else [(int(a.design[0]),float(a.design[1]),float(a.design[2]),a.design[3])]
    print(json.dumps(run(a.reps,a.reference_n,a.seed,a.smoke,a.nonadherence,grid=grid,loss=a.loss),indent=2,allow_nan=False))
