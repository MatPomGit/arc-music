"""Synthetic design diagnostics; never estimates of participant effects."""
import argparse
import json
import math
import platform
import subprocess
import numpy as np
import scipy
from scipy.stats import t, nct, norm


def welch_sim(n, sd, effect, reps=20000, seed=1729, alpha=.05, loss=0.):
    """Independent Gaussian cell means and *estimated* cell variances.

    Independent MCAR retention by cell; a replicate with <2 retained is invalid.
    Contrasts: two-arm difference or half a difference-in-differences.
    """
    n = np.asarray(n)
    sd = np.asarray(sd, dtype=float)
    if n.ndim != 1 or len(n) not in (2, 4) or sd.shape != n.shape:
        raise ValueError('invalid cells')
    if not np.issubdtype(n.dtype, np.integer) or np.any(n < 2) or not np.all(np.isfinite(sd)) or np.any(sd <= 0):
        raise ValueError('invalid n or sd')
    if not isinstance(reps, int) or isinstance(reps, bool) or reps < 2 or not math.isfinite(effect) or not 0 < alpha < 1 or not 0 <= loss < 1:
        raise ValueError('invalid parameters')
    w = np.array([-1., 1.] if len(n) == 2 else [.5, -.5, -.5, .5])
    means = effect * w / (w @ w)
    rng = np.random.default_rng(seed)
    sizes = rng.binomial(n, 1-loss, size=(reps,len(n)))
    valid = (sizes >= 2).all(axis=1)
    sizes = sizes[valid]
    if not len(sizes):
        raise ValueError('no estimable replicates')
    m = means + rng.normal(size=sizes.shape)*sd/np.sqrt(sizes)
    v = sd**2*rng.chisquare(sizes-1)/(sizes-1)
    components = w**2*v/sizes
    se2 = components.sum(axis=1)
    df = se2**2/(components**2/(sizes-1)).sum(axis=1)
    estimate = m @ w
    radius = t.ppf(1-alpha/2, df)*np.sqrt(se2)
    reject = np.abs(estimate) > radius
    cover = np.abs(estimate-effect) <= radius
    return summary(estimate, effect, reject, cover, reps)


def summary(est, truth, reject, cover, requested):
    n = len(est)
    rate = float(np.mean(reject)); coverage = float(np.mean(cover))
    z = norm.ppf(.975); d = 1+z*z/n
    center = (rate+z*z/(2*n))/d
    half = z*np.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/d
    return dict(valid=n, requested=requested, bias=float(np.mean(est)-truth),
                rejection=rate, coverage=coverage,
                mcse=float(np.sqrt(rate*(1-rate)/n)),
                rejection_ci=[float(max(0,center-half)),float(min(1,center+half))],
                coverage_mcse=float(np.sqrt(coverage*(1-coverage)/n)))


def pooled_oracle(n, effect, cells=2, alpha=.05, r2=0.):
    """Independent noncentral-t result for balanced Gaussian common variance."""
    if not isinstance(n,int) or isinstance(n,bool) or n<2 or cells not in (2,4) or not 0<alpha<1 or not 0<=r2<1 or not math.isfinite(effect):
        raise ValueError('invalid design')
    df=cells*(n-1)
    nc=effect/np.sqrt((2 if cells==2 else 1)*(1-r2)/n)
    crit=t.ppf(1-alpha/2,df)
    return float(nct.sf(crit,df,nc)+nct.cdf(-crit,df,nc))


def diary_sim(people=100, sessions=8, effect=-.25, phi=.4, missing='none', reps=500, seed=1730):
    """H6: participant FE slope; cluster sandwich CI; MNAR stress scenario.

    DGP: delayed relief = person intercept + beta*rumination + AR(1) noise.
    No baseline/relief covariates in this deliberately reduced scenario.
    Under MNAR retention depends on the unobserved follow-up disturbance.
    """
    if people<4 or sessions<3 or reps<2 or not -1<phi<1 or missing not in ('none','mar','mnar'):
        raise ValueError('invalid diary design')
    rng=np.random.default_rng(seed); estimates=[]; rejects=[]; covers=[]
    for _ in range(reps):
        x=rng.normal(size=(people,sessions))+rng.normal(size=(people,1))
        e=rng.normal(size=x.shape)
        for j in range(1,sessions): e[:,j]=phi*e[:,j-1]+np.sqrt(1-phi**2)*e[:,j]
        y=effect*x+e+rng.normal(size=(people,1))
        if missing=='none': mask=np.ones_like(x,dtype=bool)
        else:
            lp=1.5-.5*x if missing=='mar' else 1.5-.5*x-1.0*e
            mask=rng.random(x.shape)<1/(1+np.exp(-lp))
        keep=mask.sum(axis=1)>=2
        mask=mask[keep]; x=x[keep]; y=y[keep]
        g=len(x)
        if g<4: continue
        xd=(x-(x*mask).sum(axis=1,keepdims=True)/mask.sum(axis=1,keepdims=True))*mask
        yd=(y-(y*mask).sum(axis=1,keepdims=True)/mask.sum(axis=1,keepdims=True))*mask
        xx=np.sum(xd**2)
        if xx<=0: continue
        beta=np.sum(xd*yd)/xx
        score=np.sum(xd*(yd-beta*xd),axis=1)
        se=np.sqrt(g/(g-1)*np.sum(score**2)/xx**2)
        rad=t.ppf(.975,g-1)*se
        estimates.append(beta); rejects.append(abs(beta)>rad); covers.append(abs(beta-effect)<=rad)
    if not estimates: raise ValueError('no estimable replicates')
    return summary(np.array(estimates),effect,rejects,covers,reps)


def interaction_sim(n=200,effect=.3,reps=1000,seed=1731):
    """H8: randomized binary interface x continuous standard-normal expertise."""
    if n<12 or n%2 or reps<2: raise ValueError('invalid interaction design')
    rng=np.random.default_rng(seed); est=[]; rej=[]; cov=[]
    z=np.repeat([-.5,.5],n//2)
    for _ in range(reps):
        x=rng.normal(size=n); a=np.column_stack([np.ones(n),z,x,z*x])
        y=.2*z+.2*x+effect*z*x+rng.normal(size=n)
        b=np.linalg.lstsq(a,y,rcond=None)[0]; e=y-a@b
        v=np.linalg.inv(a.T@a)*((e@e)/(n-4)); rad=t.ppf(.975,n-4)*np.sqrt(v[3,3])
        est.append(b[3]); rej.append(abs(b[3])>rad); cov.append(abs(b[3]-effect)<=rad)
    return summary(np.array(est),effect,rej,cov,reps)


def novelty_sim(n=200,sessions=6,effect=-.15,phi=.4,reps=1000,seed=1732):
    """H10: between-arm contrast of person-level linear enjoyment slopes."""
    if n<8 or n%2 or sessions<3 or reps<2 or not -1<phi<1: raise ValueError('invalid novelty design')
    rng=np.random.default_rng(seed); est=[]; rej=[]; cov=[]
    time=np.arange(sessions,dtype=float); time-=time.mean()
    for _ in range(reps):
        e=rng.normal(size=(n,sessions))
        for j in range(1,sessions): e[:,j]=phi*e[:,j-1]+np.sqrt(1-phi**2)*e[:,j]
        z=np.repeat([0,1],n//2)
        y=effect*z[:,None]*time+e+rng.normal(size=(n,1))
        slopes=y@time/(time@time); a,b=np.split(slopes,2)
        v1,v2=a.var(ddof=1)/len(a),b.var(ddof=1)/len(b)
        df=(v1+v2)**2/(v1**2/(len(a)-1)+v2**2/(len(b)-1))
        diff=b.mean()-a.mean(); rad=t.ppf(.975,df)*np.sqrt(v1+v2)
        est.append(diff); rej.append(abs(diff)>rad); cov.append(abs(diff-effect)<=rad)
    return summary(np.array(est),effect,rej,cov,reps)


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--seed',type=int,default=1729)
    args=parser.parse_args(); s=args.seed
    sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    report={'sha':sha,'seed':s,'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__}
    report['welch']={f'{k}_{e}':welch_sim(n,sd,e,seed=s,loss=loss) for k,n,sd,loss in [('balanced',[88]*4,[1]*4,0),('unequal',[90,110,85,125],[.7,1.3,1.,1.5],.15)] for e in (0.,.3)}
    report['pooled_oracle']={str(k):pooled_oracle(n,.3,k) for k,n in [(2,175),(4,88)]}
    report['diary']={f'{m}_{e}':diary_sim(effect=e,missing=m,seed=s+1) for m in ('none','mar','mnar') for e in (0.,-.25)}
    report['expertise']={str(e):interaction_sim(effect=e,seed=s+2) for e in (0.,.3)}
    report['novelty']={str(e):novelty_sim(effect=e,seed=s+3) for e in (0.,-.15)}
    print(json.dumps(report,indent=2,allow_nan=False,sort_keys=True))

if __name__=='__main__': main()
