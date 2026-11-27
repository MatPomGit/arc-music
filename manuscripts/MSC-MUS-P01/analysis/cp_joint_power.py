import numpy as np
from scipy.stats import t
import json
from itertools import product

def decision(m,v,n):
    good=(n>=2).all(1)&(v>0).all(1)
    q=v/np.maximum(n,2); w=q*q/np.maximum(n-1,1)
    s=np.column_stack([m[:,0]-m[:,1],m[:,3]-m[:,2]])
    se2=np.column_stack([q[:,:2].sum(1),q[:,2:].sum(1)])
    df=se2**2/np.column_stack([w[:,:2].sum(1),w[:,2:].sum(1)])
    p=t.sf(s/np.sqrt(se2),df); rad=t.ppf(.975,df)*np.sqrt(se2)
    psi=s.mean(1); pv=q.sum(1)/4; pr=t.ppf(.975,q.sum(1)**2/w.sum(1))*np.sqrt(pv)
    return good,good&(p.max(1)<=.05),s,rad,psi,pr

def run(reps=20000,seed=20261203):
    effects=[(0.,0.),(.3,.3),(.15,.45),(.45,.15),(0.,.6),(.6,0.),(-.1,.7),(.7,-.1)]
    profiles={'equal':([1.]*4,[.85]*4),'heterogeneous':([.8,1.2,1.2,.8],[.9,.8,.75,.9])}
    grid=list(product((420,600,800,1000,1200,1400),effects,profiles))
    out=[]
    for (n,e,profile),ss in zip(grid,np.random.SeedSequence(seed).spawn(len(grid))):
        rng=np.random.default_rng(ss); sd,ret=map(np.array,profiles[profile]); count=rng.binomial(n//4,ret,size=(reps,4)); m=np.array([e[0],0,0,e[1]])+rng.normal(size=count.shape)*sd/np.sqrt(np.maximum(count,1)); df=np.maximum(count-1,1); v=sd**2*rng.chisquare(df)/df
        ok,success,s,rad,psi,pr=decision(m,v,count); error=s[ok]-e; pe=psi[ok]-np.mean(e); p=success.mean()
        out.append(dict(n=n,e=e,profile=profile,requested=reps,valid=int(ok.sum()),failed=int((~ok).sum()),joint=float(p),mcse=float(np.sqrt(p*(1-p)/reps)),psi_positive=float((ok&(psi-pr>0)).mean()),bias=error.mean(0).tolist(),rmse=np.sqrt((error**2).mean(0)).tolist(),coverage=(np.abs(error)<=rad[ok]).mean(0).tolist(),psi_coverage=float((np.abs(pe)<=pr[ok]).mean())))
    return out
if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description="Synthetic CP conjunction calibration")
    parser.add_argument("--reps",type=int,default=20000)
    parser.add_argument("--seed",type=int,default=20261203)
    args=parser.parse_args()
    if args.reps<1:parser.error("Positive replication count required")
    print(json.dumps(run(args.reps,args.seed),indent=2,allow_nan=False))
