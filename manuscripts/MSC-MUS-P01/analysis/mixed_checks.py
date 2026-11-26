"""Prospective H6/H10 Gaussian mixed likelihood and missingness diagnostics.
Synthetic scenarios only. Profile ML integrates correlated Gaussian random
intercept/slope and an AR(1) residual with an estimated variance modifier.
"""
import argparse
import json
import subprocess
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import t, norm
from longitudinal_checks import design, fit, summarize


def blocks(x, y, mask, n, k, kind):
    xx=x.reshape(n,k,-1); yy=y.reshape(n,k); mm=mask.reshape(n,k)
    slope=xx[:,:,1] if kind=='h6' else xx[:,:,2]
    # H6 observed baseline distress (within + between); H10 randomised arm.
    scale=xx[:,:,3]+xx[:,:,4] if kind=='h6' else xx[:,:,1]
    result=[]
    patterns=np.unique(mm,axis=0)
    for pattern in patterns:
        if not pattern.any(): continue
        ii=np.flatnonzero((mm==pattern).all(axis=1)); jj=np.flatnonzero(pattern)
        z=np.stack([np.ones((len(ii),len(jj))),slope[ii][:,jj]],axis=-1)
        result.append((xx[ii][:,jj],yy[ii][:,jj],z,scale[ii][:,jj],np.abs(jj[:,None]-jj)))
    return result


def covariance(theta,z,v,distance):
    # Positive-definite random effect covariance via Cholesky; AR correlation.
    l=np.array([[np.exp(theta[0]),0.],[theta[1],np.exp(theta[2])]])
    phi=np.tanh(theta[4])
    sd=np.exp(theta[3]+theta[5]*np.clip(v,-5.,5.))
    return (z@l)@np.swapaxes(z@l,-1,-2)+sd[:,:,None]*sd[:,None,:]*phi**distance


def profile(theta, data, details=False):
    p=data[0][0].shape[-1]
    information=np.zeros((p,p)); rhs=np.zeros(p); quadratic=0.; logdet=0.; count=0
    for x,y,z,v,distance in data:
        cov=covariance(theta,z,v,distance)
        l=np.linalg.cholesky(cov)
        wx=np.linalg.solve(l,x); wy=np.linalg.solve(l,y[...,None])[...,0]
        information+=np.einsum('nki,nkj->ij',wx,wx)
        rhs+=np.einsum('nki,nk->i',wx,wy)
        quadratic+=np.sum(wy**2)
        logdet+=2*np.log(np.diagonal(l,axis1=-2,axis2=-1)).sum()
        count+=y.size
    beta=np.linalg.solve(information,rhs)
    nll=.5*(count*np.log(2*np.pi)+logdet+quadratic-rhs@beta)
    return (float(nll),beta,np.linalg.inv(information)) if details else float(nll)


def mixed_fit(x,y,mask,n,k,kind,contrast):
    data=blocks(x,y,mask,n,k,kind)
    if not data or mask.sum()<=x.shape[1]: raise ValueError('insufficient data')
    bounds=[(-5,3),(-3,3),(-5,2),(-5,3),(-2.5,2.5),(-1,1)]
    start=np.array([0.,0.,-1.,-.1,.3,0.])
    opt=minimize(profile,start,args=(data,),method='L-BFGS-B',bounds=bounds,
                 options={'maxiter':160,'ftol':1e-8})
    if not opt.success or not np.isfinite(opt.fun): raise ValueError('mixed fit did not converge')
    nll,beta,cov=profile(opt.x,data,True)
    rad=t.ppf(.975,n-1)*np.sqrt(contrast@cov@contrast)
    return dict(estimate=float(contrast@beta),radius=float(rad),nll=nll,
                theta=opt.x.tolist(),beta=beta.tolist(),
                at_boundary=bool(any(abs(a-lo)<1e-4 or abs(a-hi)<1e-4 for a,(lo,hi) in zip(opt.x,bounds))))


def logistic(x,y):
    # Small fixed ridge on slopes for finite fits under separation.
    if len(np.unique(y))==1: return np.full(len(y),float(y[0])),None
    def objective(b):
        eta=x@b
        return float(np.sum(np.logaddexp(0.,eta)-y*eta)+.005*(b[1:]@b[1:]))
    def grad(b):
        return x.T@(expit(x@b)-y)+np.r_[0.,.01*b[1:]]
    opt=minimize(objective,np.zeros(x.shape[1]),jac=grad,method='BFGS',
                 options={'gtol':1e-6})
    if not opt.success and np.linalg.norm(grad(opt.x))>1e-4:
        raise ValueError('propensity fit did not converge')
    return expit(x@opt.x),opt.x


def estimated_probability(x,y,mask,n,k,kind):
    xx=x.reshape(n,k,-1); yy=y.reshape(n,k); mm=mask.reshape(n,k)
    if kind not in ('h6','h10'):
        raise ValueError('unknown design')
    if kind=='h10' and (not mm[:,0].all() or np.any(mm[:,1:] & ~mm[:,:-1])):
        raise ValueError('H10 requires observed baseline and monotone dropout')
    if mask.all(): return np.ones(n*k)
    if kind=='h6':
        # Reconstruct observed Q and baseline D from within/between columns.
        a=np.column_stack([np.ones(n*k),x[:,1]+x[:,2],x[:,3]+x[:,4]])
        pred,_=logistic(a,mask.astype(float))
        return np.maximum(pred,.025)
    # Discrete-time hazard conditional only on previously observed history.
    risk=mm[:,:-1]
    arm=xx[:,1:,1][risk]; previous=yy[:,:-1][risk]
    a=np.column_stack([np.ones(len(arm)),arm,previous])
    retained=mm[:,1:][risk].astype(float)
    predicted,b=logistic(a,retained)
    prob=np.ones((n,k))
    for j in range(1,k):
        active=mm[:,j-1]
        # Degenerate response: use the constant fitted hazard, not survival=1.
        hazard=predicted[0] if b is None else expit(
            b[0]+b[1]*xx[active,j,1]+b[2]*yy[active,j-1])
        prob[active,j]=prob[active,j-1]*hazard
        # After dropout, no further observed history is available. These
        # carried-forward values are NOT used as weights for missing outcomes.
        prob[~active,j]=prob[~active,j-1]
    return np.maximum(prob.ravel(),.025)


def sensitivity(x,y,mask,n,k,kind,c):
    """Marginal pattern-mixture point estimates; fixed delta, not identified."""
    g=np.repeat(np.arange(n),k)
    _,_,beta=fit(x[mask],y[mask],g[mask],c)
    base=x@beta
    # H6 shift in within-person Q slope; H10 arm-specific time-dependent shift.
    modifier=x[:,1] if kind=='h6' else x[:,3]
    results=[]
    for delta in (-.5,0.,.5):
        completed=np.where(mask,y,base+delta*modifier)
        results.append(fit(x,completed,g,c)[0])
    return np.array(results)


def bootstrap(x,y,mask,n,k,kind,c,reps=199,seed=1732):
    """Participant bootstrap refits outcome regression and propensity.
    Percentile intervals are conditional on fixed delta and observed predictors.
    No unobserved follow-up outcomes are accessed.
    """
    g=np.repeat(np.arange(n),k)
    est=sensitivity(x,y,mask,n,k,kind,c)
    p=estimated_probability(x,y,mask,n,k,kind)
    ipw=fit(x[mask],y[mask],g[mask],c,1/p[mask])[0]
    rng=np.random.default_rng(seed); out=[]; weights=[]
    for _ in range(reps):
        ids=rng.integers(0,n,n); ix=(ids[:,None]*k+np.arange(k)).ravel()
        xb,yb,mb=x[ix],y[ix],mask[ix]
        try:
            v=sensitivity(xb,yb,mb,n,k,kind,c)
            pb=estimated_probability(xb,yb,mb,n,k,kind)
            w=fit(xb[mb],yb[mb],g[mb],c,1/pb[mb])[0]
        except (ValueError,np.linalg.LinAlgError):
            continue
        out.append(v); weights.append(w)
    if len(out)<.9*reps: raise ValueError('bootstrap failure rate exceeds 10%')
    return dict(delta=[-.5,0.,.5],estimate=est.tolist(),
                intervals=np.quantile(out,[.025,.975],axis=0).T.tolist(),
                ipw_estimate=ipw,ipw_interval=np.quantile(weights,[.025,.975]).tolist(),
                valid=len(out),requested=reps,weight_cap=40)


def wilson(successes,total,alpha=.05):
    """Binomial Monte Carlo interval, including zero/all successes."""
    if total<=0 or not 0<=successes<=total:
        raise ValueError('invalid binomial count')
    z=norm.ppf(1-alpha/2)
    q=successes/total
    den=1+z*z/total
    center=(q+z*z/(2*total))/den
    radius=z*np.sqrt(q*(1-q)/total+z*z/(4*total**2))/den
    return [max(0.,center-radius),min(1.,center+radius)]


def diagnostic_summary(values,truth,requested):
    result=summarize(values,truth,requested)
    a=np.asarray(values)
    est,rad=a.T
    valid=len(est)
    result.update(failed=requested-valid,
                  valid_fraction=valid/requested,
                  rejection_mc_interval=wilson(int(np.sum(np.abs(est)>rad)),valid),
                  coverage_mc_interval=wilson(int(np.sum(np.abs(est-truth)<=rad)),valid),
                  bias_mcse=float(np.std(est,ddof=1)/np.sqrt(valid)) if valid>1 else None)
    return result


def scenario(kind,missing,effect,n=80,k=8,reps=20,seed=1732):
    rng=np.random.default_rng(seed); mixed=[]; weighted=[]; boundary=0
    for _ in range(reps):
        x,y,g,c,m,_,_=design(rng,kind,n,k,effect,missing)
        # Explicitly mask outcomes before estimation; DGP oracle probabilities discarded.
        y=np.where(m,y,np.nan)
        try:
            v=mixed_fit(x,y,m,n,k,kind,c)
            mixed.append((v['estimate'],v['radius'])); boundary+=v['at_boundary']
        except (ValueError,np.linalg.LinAlgError):
            pass
        try:
            p=estimated_probability(x,y,m,n,k,kind)
            weighted.append(fit(x[m],y[m],g[m],c,1/p[m])[:2])
        except (ValueError,np.linalg.LinAlgError):
            pass
    x,y,g,c,m,_,_=design(rng,kind,n,k,effect,missing)
    y=np.where(m,y,np.nan)
    return dict(mixed=diagnostic_summary(mixed,effect,reps),
                ipw=diagnostic_summary(weighted,effect,reps),
                boundary=boundary,boundary_mc_interval=wilson(boundary,len(mixed)),
                sensitivity=bootstrap(x,y,m,n,k,kind,c,seed=seed+1))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reps',type=int,default=20);p.add_argument('--seed',type=int,default=1732)
    p.add_argument('--n',type=int,default=80);p.add_argument('--k',type=int,default=8)
    a=p.parse_args()
    if a.reps<2 or a.n<40 or a.n%2 or a.k<4:
        p.error('require reps>=2, even n>=40 and k>=4')
    out={'sha':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
         'seed':a.seed,'reps':a.reps,'n':a.n,'k':a.k}
    for kind,effect in [('h6',-.25),('h10',-.35)]:
        out[kind]={f'{mode}_{e}':scenario(kind,mode,e,n=a.n,k=a.k,reps=a.reps,seed=a.seed) for mode in ('none','mar','mnar') for e in (0.,effect)}
    print(json.dumps(out,indent=2,allow_nan=False))

if __name__=='__main__': main()
