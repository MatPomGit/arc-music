"""Synthetic bounded 0--10 CP calibration; no participant data."""
import argparse
import json
from itertools import product
import numpy as np
from scipy.special import expit
from scipy.stats import betabinom, t

SCORES=np.arange(11)
EFFECTS=((0.,0.),(.3,.3),(.15,.45),(0.,.6),(-.1,.7))
CENTRES=(.15,.5,.85)
MECHANISMS=("complete","mcar","mar","mnar")

def probabilities(centre,effect,mechanism,concentration):
    # X is a binary pre-assignment prognostic factor with P(X=1)=.5.
    # The beta-binomial mean is exactly 10*p; no clipping or latent-scale
    # approximation is needed for the full-population simple effects.
    p=centre+np.array([-.06,.06])+effect/10
    if np.any((p<=0)|(p>=1)) or concentration<=0:
        raise ValueError("Invalid bounded mean or concentration")
    pmf=.5*betabinom.pmf(SCORES[None,:],10,p[:,None]*concentration,(1-p[:,None])*concentration)
    x=np.array([-1.,1.])[:,None]
    if mechanism=="complete":ret=np.ones_like(pmf)
    elif mechanism=="mcar":ret=np.full_like(pmf,.85)
    elif mechanism=="mar":ret=np.broadcast_to(expit(1.9+.9*x),pmf.shape)
    elif mechanism=="mnar":ret=expit(1.9+.9*x+.38*(SCORES[None,:]-5))
    else:raise ValueError("Unknown observation mechanism")
    probs=np.stack((pmf*ret,pmf*(1-ret)),axis=-1)
    return probs/probs.sum()

def moments(counts):
    n=counts.sum(-1)
    mean=(counts*SCORES).sum(-1)/np.maximum(n,1)
    ss=(counts*(SCORES-mean[...,None])**2).sum(-1)
    v=ss/np.maximum(n-1,1)
    return n,mean,v

def infer(counts,method,truth):
    # counts: replication, assigned cell, X stratum, observed score.
    if method=="available":
        n,m,v=moments(counts.sum(2))
        good=(n>=2).all(1)&(v>0).all(1)
        q=v/np.maximum(n,1)
        w=q*q/np.maximum(n-1,1)
    else:
        n,means,v=moments(counts)
        good=(n>=2).all((1,2))
        m=means.mean(2)
        q0=v/np.maximum(n,1)/4
        q=q0.sum(2)
        w=(q0*q0/np.maximum(n-1,1)).sum(2)
        good &= (q>0).all(1)
    s=np.column_stack((m[:,0]-m[:,1],m[:,3]-m[:,2]))
    se2=np.column_stack((q[:,:2].sum(1),q[:,2:].sum(1)))
    denom=np.column_stack((w[:,:2].sum(1),w[:,2:].sum(1)))
    good &= (denom>0).all(1)&(se2>0).all(1)
    with np.errstate(divide="ignore",invalid="ignore"):
        df=se2**2/denom
        p=t.sf(s/np.sqrt(se2),df)
        radius=t.ppf(.975,df)*np.sqrt(se2)
    good &= np.isfinite(p).all(1)&np.isfinite(radius).all(1)
    reject=good&(p.max(1)<=.05)
    errors=s[good]-truth
    rate=float(reject.mean())
    k=int(good.sum())
    return dict(valid=k,failed=len(good)-k,joint=rate,
                mcse=float(np.sqrt(rate*(1-rate)/len(good))),
                bias=errors.mean(0).tolist() if k else None,
                rmse=np.sqrt((errors**2).mean(0)).tolist() if k else None,
                coverage=(np.abs(errors)<=radius[good]).mean(0).tolist() if k else None)

def run(reps=2000,seed=20261128,grid=None):
    if reps<1:raise ValueError("Positive replication count required")
    if grid is None:
        grid=list(product((420,1000,1400),EFFECTS,CENTRES,MECHANISMS,(8.,40.)))
    grid=list(grid)
    cells=[]
    for (n,e,centre,mechanism,concentration),ss in zip(grid,np.random.SeedSequence(seed).spawn(len(grid))):
        if n<40 or n%4 or len(e)!=2 or not np.isfinite(e).all():
            raise ValueError("Invalid design")
        rng=np.random.default_rng(ss)
        effects=(e[0],0.,0.,e[1])
        counts=np.stack([rng.multinomial(n//4,probabilities(centre,delta,mechanism,concentration).ravel(),size=reps).reshape(reps,2,11,2) for delta in effects],axis=1)
        observed=counts[...,0]
        cells.append(dict(n=n,e=list(e),centre=centre,mechanism=mechanism,concentration=concentration,
                          requested=reps,mean_retention=float(observed.sum((1,2,3)).mean()/n),
                          union_null=min(e)<=0,
                          methods={method:infer(observed,method,np.asarray(e)) for method in ("available","standardised")}))
    return dict(status="SYNTHETIC_DEVELOPMENT",seed=seed,reps=reps,confirmatory_authorized=False,cells=cells)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reps",type=int,default=2000)
    p.add_argument("--seed",type=int,default=20261128)
    p.add_argument("--smoke",action="store_true")
    a=p.parse_args()
    grid=list(product((420,),((0.,.6),(.3,.3)),(.15,.85),MECHANISMS,(8.,))) if a.smoke else None
    print(json.dumps(run(a.reps,a.seed,grid),indent=2,allow_nan=False))
