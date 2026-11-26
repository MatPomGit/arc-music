"""Paired synthetic missing-outcome calibration; no empirical data."""
import numpy as np
from scipy.special import expit
from scipy.optimize import brentq, minimize
from itertools import product
import argparse
import json

def slope(g,x,y,w=None):
    _,g=np.unique(g,return_inverse=True); keep=np.bincount(g)[g]>=2
    g,x,y=g[keep],x[keep],y[keep]; w=np.ones(len(y)) if w is None else w[keep]
    _,g=np.unique(g,return_inverse=True); G=len(np.unique(g))
    if G<10: raise ValueError('Too few clusters')
    total=np.bincount(g,weights=w); xm=np.zeros((G,x.shape[1])); ym=np.zeros(G)
    np.add.at(xm,g,x*w[:,None]); np.add.at(ym,g,y*w)
    x=(x-xm[g]/total[g,None])*np.sqrt(w[:,None]); y=(y-ym[g]/total[g])*np.sqrt(w)
    if np.linalg.matrix_rank(x)<x.shape[1]: raise ValueError('Rank deficient')
    return np.linalg.lstsq(x,y,rcond=None)[0]

def probability(x,obs):
    scale=x.std(axis=0); z=np.column_stack([np.ones(len(x)),(x-x.mean(axis=0))/np.where(scale>0,scale,1)])
    def obj(b):
        v=z@b; return np.logaddexp(0,v).sum()-obs@v+.5*np.sum(b[1:]**2)
    def grad(b): return z.T@(expit(z@b)-obs)+np.r_[0,b[1:]]
    opt=minimize(obj,np.zeros(z.shape[1]),jac=grad,method='BFGS')
    if not opt.success and np.linalg.norm(grad(opt.x))>1e-5: raise ValueError('Observation fit failed')
    return expit(z@opt.x)

def replicate(rng,n,m,beta,missing,kind):
    g=np.repeat(np.arange(n),m); day=np.tile(np.arange(1,m+1),n); u=rng.normal(size=n)
    a=np.clip(np.rint(5+.5*u[g]+rng.normal(0,2,n*m)),0,10)
    d=np.clip(np.rint(5+.4*u[g]+rng.normal(0,1.8,n*m)),0,10)
    k=np.clip(np.rint(5+rng.normal(0,2,n*m)),0,10)
    x=np.column_stack([a,d,k,day]); b=rng.normal(beta,.35,n)
    e=rng.normal(size=(n,m))*rng.lognormal(np.log(1.5),.30,n)[:,None]
    for j in range(1,m): e[:,j]=.4*e[:,j-1]+np.sqrt(.84)*e[:,j]
    y=np.clip(np.rint(5+u[g]+b[g]*(a-5)+.2*(d-5)+.15*(k-5)+.02*day+e.ravel()),0,10)
    risk=np.zeros(len(y)) if kind=='mcar' else .25*(d-5)+.1*(a-5)
    if kind=='mnar': risk=risk+.45*(y-5)+.15*(a-5)*(y-5)
    z=brentq(lambda z:expit(z+risk).mean()-missing,-40,40)
    obs=rng.random(len(y))>=expit(z+risk)
    target=slope(g,x,y)[0]; cc=slope(g[obs],x[obs],y[obs]); p=probability(x,obs)
    w=1/np.maximum(p[obs],.05)
    ipw=[slope(g[obs],x[obs],y[obs],np.minimum(w,cap))[0] for cap in [10,20]]
    count=np.bincount(g[obs],minlength=n); residual=np.bincount(g[obs],weights=y[obs]-x[obs]@cc,minlength=n)
    included=count[g]>0; offset=np.divide(residual,count,out=np.zeros(n),where=count>0)
    pred=offset[g]+x@cc; ac=a-np.bincount(g,weights=a)[g]/m
    shifts=[]
    for s,k in product([-2,-1,0,1,2],[-1,0,1]):
        yy=np.where(obs,y,np.clip(pred+s+k*ac/2,0,10)); shifts.append(slope(g[included],x[included],yy[included])[0])
    return [target,cc[0],*ipw,min(shifts),max(shifts),obs.mean(),p.min(),(count==0).sum()]

def run(seed=2608,reps=200,n=160,m=6):
    rng=np.random.default_rng(seed); cells=[]
    for beta,missing,kind in product([0,.15],[.3,.45],['mcar','mar','mnar']):
        rows=[]; failures=0
        for _ in range(reps):
            try: rows.append(replicate(rng,n,m,beta,missing,kind))
            except (ValueError,np.linalg.LinAlgError): failures+=1
        if not rows: raise ValueError('All replicates failed')
        a=np.array(rows); target=a[:,0]; estimators={}
        for name,j in [('cc',1),('ipw10',2),('ipw20',3)]:
            err=a[:,j]-target
            estimators[name]={'bias':float(err.mean()),'mcse':float(err.std(ddof=1)/np.sqrt(len(err))) if len(err)>1 else None,'rmse':float(np.sqrt(np.mean(err**2)))}
        cells.append(dict(beta=beta,missing=missing,mechanism=kind,valid=len(rows),failures=failures,estimators=estimators,envelope=float(np.mean((a[:,4]<=target)&(target<=a[:,5]))),width=float(np.mean(a[:,5]-a[:,4])),observed=float(a[:,6].mean()),min_p=float(a[:,7].mean()),no_outcome=float(a[:,8].mean())))
    return dict(status='SYNTHETIC_PAIRED',seed=seed,reps=reps,n=n,m=m,cells=cells)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--reps',type=int,default=200)
    a=p.parse_args()
    if a.reps<1: p.error('Positive replication count required')
    print(json.dumps(run(reps=a.reps),indent=2,allow_nan=False))
