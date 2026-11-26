"""Synthetic invariant and noninvariant groups, including unequal latent distributions."""
import argparse,json
import numpy as np
from invariance import compare_groups
from robust_calibration import wilson

def group(n,rng,scenario,second):
    d=np.repeat(np.arange(2),4)
    l=np.full(8,.65); cuts=np.tile([-.85,-.25,.25,.85],(8,1))
    mean=np.zeros(2); sd=np.ones(2)
    if second:
        mean=np.array([.35,-.3]); sd=np.array([1.25,.8])
        if scenario=="threshold_dif":
            cuts[2,1]+=.35
        if scenario=="loading_dif":
            l[2]=.35
        if scenario=="intercept_dif":
            cuts[2]-=.45
    phi=np.array([[1,.35],[.35,1]])*sd[:,None]*sd[None,:]
    eta=rng.multivariate_normal(mean,phi,size=n)
    # Residual SD refers to reference group for invariant indicators.
    z=eta[:,d]*l+np.sqrt(1-.65**2)*rng.normal(size=(n,8))
    return np.sum(z[:,:,None]>cuts[None,:,:],axis=2)

def run(reps=30,seed=20261130):
    rng=np.random.default_rng(seed); d=np.repeat(np.arange(2),4); output=[]
    for scenario in ("invariant","threshold_dif","loading_dif","intercept_dif"):
        records=[]
        for i in range(reps):
            try:
                result=compare_groups(group(250,rng,scenario,False),group(250,rng,scenario,True),d)
                records.append({"replicate":i,"status":"proper",**result})
            except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
                records.append({"replicate":i,"status":"failure","reason":str(exc)})
        proper=[x for x in records if x["status"]=="proper"]
        summaries={}
        for name in ("threshold_shape","threshold_loading","threshold_loading_intercept"):
            rejected=sum(x["tests"][name]["p_value"]<.05 for x in proper)
            summaries[name]={"rejected":rejected,"unconditional_rate":rejected/reps,
                             "conditional_rate":rejected/len(proper) if proper else None,
                             "conditional_interval":wilson(rejected,len(proper)) if proper else None}
        output.append({"scenario":scenario,"requested":reps,"proper":len(proper),
                       "proper_interval":wilson(len(proper),reps),"tests":summaries,"records":records})
    return {"label":"SYNTHETIC DEVELOPMENT ONLY; two-group diagnostics, not validated WLSMV",
            "seed":seed,"n_per_group":250,"scenarios":output}

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--reps",type=int,default=30)
    a=p.parse_args()
    if a.reps<1: p.error("positive replication count required")
    print(json.dumps(run(a.reps),indent=2,allow_nan=False))
