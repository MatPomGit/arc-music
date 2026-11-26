import json, numpy as np
from scipy.special import expit
from scipy.optimize import brentq
from scipy.stats import t

def draw(rng,n,m,beta,drop,kind,rho):
    g=np.repeat(np.arange(n),m); day=np.tile(np.arange(1,m+1),n); u=rng.normal(size=n)
    a=np.clip(np.rint(5+.5*u[g]+rng.normal(0,2,n*m)),0,10)
    d=np.clip(np.rint(5+.4*u[g]+rng.normal(0,1.8,n*m)),0,10)
    k=np.clip(np.rint(5+rng.normal(0,2,n*m)),0,10)
    b=rng.normal(beta,.35,n); e=rng.normal(size=(n,m))*rng.lognormal(np.log(1.5),.30,n)[:,None]
    for j in range(1,m): e[:,j]=rho*e[:,j-1]+np.sqrt(1-rho*rho)*e[:,j]
    y=np.clip(np.rint(5+u[g]+b[g]*(a-5)+.2*(d-5)+.15*(k-5)+.02*day+e.ravel()),0,10)
    x=np.column_stack([a,d,k,day]); keep=np.ones((n,m),bool)
    if drop:
        risk=.25*(d.reshape(n,m)[:,1:]-5)
        if kind=='mnar': risk+=.35*(y.reshape(n,m)[:,1:]-5)
        z=brentq(lambda z: np.mean(1-np.prod(1-expit(z+risk),axis=1))-drop,-40,40)
        keep[:,1:]=np.cumprod(rng.random((n,m-1))>=expit(z+risk),axis=1).astype(bool)
    return g[keep.ravel()],x[keep.ravel()],y[keep.ravel()],keep[:,-1].mean()

def fit(g,x,y):
    _,g=np.unique(g,return_inverse=True); counts=np.bincount(g); keep=counts[g]>=2
    x,y,g=x[keep],y[keep],g[keep]; _,g=np.unique(g,return_inverse=True); counts=np.bincount(g)
    G,N,p=len(counts),len(y),x.shape[1]
    if G<10 or N-G-p<=0: raise ValueError('Insufficient clusters')
    xm=np.zeros((G,p)); ym=np.zeros(G); np.add.at(xm,g,x); np.add.at(ym,g,y)
    x=x-xm[g]/counts[g,None]; y=y-ym[g]/counts[g]
    bread=np.linalg.inv(x.T@x); b=bread@x.T@y; resid=y-x@b
    s=np.zeros((G,p)); np.add.at(s,g,x*resid[:,None]); v=(bread@(s.T@s)@bread)[0,0]
    return b[0],np.sqrt(v*G/(G-1)*(N-1)/(N-G-p)),np.sqrt(v*G/(G-1)*(N-1)/(N-p)),t.ppf(.975,G-1),G,N

def run(seed=2607,reps=300,reference_n=30000):
    rng=np.random.default_rng(seed); cells=[]
    for m in [4,6,10]:
        rho={4:.1,6:.4,10:.7}[m]
        for beta in [0,.15]:
            ref=fit(*draw(rng,reference_n,m,beta,0,'mar',rho)[:3]); target=0 if beta==0 else float(ref[0])
            for drop in [.15,.30,.45]:
                for kind in ['mar','mnar']:
                    rows=[]; fail=0
                    for _ in range(reps):
                        g,x,y,ret=draw(rng,160,m,beta,drop,kind,rho)
                        try: rows.append((*fit(g,x,y),ret))
                        except (ValueError,np.linalg.LinAlgError): fail+=1
                    b,s,sn,c,G,N,ret=np.array(rows).T
                    out=dict(m=m,rho=rho,beta=beta,drop=drop,kind=kind,target=target,ref_se=float(ref[1]),valid=len(rows),fail=fail,bias=float(np.mean(b-target)),retention=float(ret.mean()),clusters=float(G.mean()),sessions=float(N.mean()))
                    for label,se in [('full',s),('nested',sn)]:
                        rate=float(np.mean(abs(b)>c*se)); out[label]=dict(rejection=rate,coverage=float(np.mean(abs(b-target)<=c*se)),mcse=float(np.sqrt(rate*(1-rate)/len(rows))))
                    cells.append(out)
    return dict(status='SYNTHETIC',n=160,seed=seed,reps=reps,reference_n=reference_n,cells=cells)
if __name__=='__main__': print(json.dumps(run(),indent=2,allow_nan=False))
