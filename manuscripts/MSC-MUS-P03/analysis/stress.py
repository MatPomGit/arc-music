"""Synthetic H1 stress tests; projection target calibrated before missingness."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.special import expit
from scipy.stats import t
from power import covariates, calibration, wilson, CAP, TARGET


def generate(rng, n, rho, beta, discrete):
    x = covariates(rng, n, rho)
    if discrete:
        x[:, 1:6] = np.rint(x[:, 1:6])
        x[:, 7] = np.rint(x[:, 7])
    y = 5 + .25*(x[:,5]-5) + beta*(x[:,1]-5) + .12*(x[:,2]-5) + rng.uniform(-2,2,n)
    if discrete:
        y = np.rint(y)
    return x, y


def estimate(x, y):
    n,p=x.shape
    inv=np.linalg.inv(x.T@x)
    coef=inv@x.T@y
    residual=y-x@coef
    h=np.einsum('ij,jk,ik->i',x,inv,x)
    variance=(inv@(x.T@(x*(residual/(1-h))[:,None]**2))@inv)[1,1]
    se=np.sqrt(variance)
    return coef[1],t.ppf(.975,n-p)*se


def simulate(reps=2000, seed=2718):
    rows=[]
    for r in (0.,.15):
        beta=calibration(.6,r)
        for discrete in (False,True):
            # Estimate the full-data linear projection using an independent large reference.
            x,y=generate(np.random.default_rng(seed+1),500_000,.6,beta,discrete)
            target=float(np.linalg.lstsq(x,y,rcond=None)[0][1]) if discrete else beta
            # For rounded null data symmetry and independence conditional on covariates
            # are not assumed: report the calibrated projection, not a null p-value.
            for mechanism in ('complete','MAR-predictor','MNAR-interaction'):
                rng=np.random.default_rng(np.random.SeedSequence([seed,int(r*100),int(discrete),('complete','MAR-predictor','MNAR-interaction').index(mechanism)]))
                values=[]
                for _ in range(reps):
                    x,y=generate(rng,CAP,.6,beta,discrete)
                    probability=np.zeros(CAP)
                    if mechanism=='MAR-predictor':
                        probability=expit(-1.9+.20*(y-5)+.1*(x[:,5]-5))
                    elif mechanism=='MNAR-interaction':
                        probability=expit(-1.9+.25*(5-y)+.15*(x[:,1]-5)*(y-5))
                    ids=np.flatnonzero(rng.random(CAP)>=probability)[:TARGET]
                    point,half=estimate(x[ids],y[ids])
                    values.append((len(ids),point,abs(point-target)<=half,abs(point)>half))
                a=np.asarray(values)
                hits=int(a[:,2].sum()); rejects=int(a[:,3].sum())
                rows.append(dict(partial_r=r,discrete=discrete,mechanism=mechanism,reps=reps,target=target,mean_n=float(a[:,0].mean()),attainment=float(np.mean(a[:,0]==TARGET)),bias=float(a[:,1].mean()-target),coverage=hits/reps,coverage_ci95=wilson(hits,reps),rejection=rejects/reps,rejection_ci95=wilson(rejects,reps)))
    return dict(data_kind='synthetic',seed=seed,scenarios=rows)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reps',type=int,default=2000)
    p.add_argument('--seed',type=int,default=2718)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.reps<1:
        p.error('reps must be positive')
    a.out.write_text(json.dumps(simulate(a.reps,a.seed),indent=2,allow_nan=False)+'\n')
