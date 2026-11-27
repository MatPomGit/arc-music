"""Development diagnostics for the actual P03 donor-matching sampler.

Scalar trace screens cannot establish joint FCS compatibility. Never treat
a failed, degenerate, or insufficient trace as evidence of convergence.
"""
import argparse
import json
from collections import defaultdict
import numpy as np
from scipy.stats import rankdata, norm
from imputation import draw_imputations, pool, matrix
from models import MODELS, SOURCES, fit, prepare
from intake import read_records


def rank_normalize(x):
    r=rankdata(x.ravel(),method="average").reshape(x.shape)
    return norm.ppf((r-.375)/(x.size+.25))


def rhat(x):
    n=x.shape[1]
    w=x.var(axis=1,ddof=1).mean()
    b=n*x.mean(axis=1).var(ddof=1)
    return float(np.sqrt(((n-1)*w/n+b/n)/w)) if w>0 else None


def ess(x):
    m,n=x.shape
    w=x.var(axis=1,ddof=1).mean()
    b=n*x.mean(axis=1).var(ddof=1)
    v=(n-1)*w/n+b/n
    if v<=0:
        return None
    centered=x-x.mean(axis=1,keepdims=True)
    acov=np.stack([np.correlate(row,row,mode="full")[n-1:]/n for row in centered])
    rho=np.r_[1.,1-(w-acov.mean(axis=0)[1:])/v]
    pairs=[]
    for j in range(0,n-1,2):
        pair=float(rho[j]+rho[j+1])
        if pair<=0:
            break
        pairs.append(min(pair,pairs[-1]) if pairs else pair)
    return float(min(m*n,m*n/max(1.,-1+2*sum(pairs))))


def diagnose(x):
    x=np.asarray(x,float)
    if x.ndim!=2 or x.shape[0]<4 or x.shape[1]<20 or not np.isfinite(x).all():
        return dict(status="insufficient_or_invalid",rhat=None,bulk_ess=None,tail_ess=None)
    n=x.shape[1]//2
    x=np.concatenate([x[:,:n],x[:,-n:]])
    if np.ptp(x)==0:
        return dict(status="constant_trace",rhat=None,bulk_ess=None,tail_ess=None)
    z=rank_normalize(x)
    a,b=rhat(z),rhat(rank_normalize(abs(x-np.median(x))))
    bulk=ess(z)
    tail=[ess((x<=np.quantile(x,.05)).astype(float)),
          ess((x>=np.quantile(x,.95)).astype(float))]
    if a is None or b is None or bulk is None or any(v is None for v in tail):
        return dict(status="degenerate_trace",rhat=None,bulk_ess=None,tail_ess=None)
    rh=max(1.,a,b)
    te=min(tail)
    return dict(status="screen_pass" if rh<=1.01 and min(bulk,te)>=400 else "screen_flag",
                rhat=rh,bulk_ess=bulk,tail_ess=te)


def scalar_summaries(work,masks):
    out={}
    for k,mask in masks.items():
        if not mask.any():
            continue
        x=work.loc[mask,k]
        if k=="source":
            for c in SOURCES:
                out[k+":p_"+c]=float(x.eq(c).mean())
            continue
        x=x.to_numpy(float)
        out[k+":mean"]=float(x.mean())
        out[k+":sd"]=float(x.std())
        if k in ("clarity_post","motive_expression","clarity_pre"):
            for cut in (2,5,8):
                out[k+":cdf_"+str(cut)]=float((x<=cut).mean())
        if k in ("clarity_post","motive_expression"):
            for j in ("clarity_pre","motive_mood","motive_expression","clarity_post"):
                if j==k: continue
                y=work.loc[mask,j].to_numpy(float)
                out[k+":corr_"+j]=float(np.corrcoef(x,y)[0,1]) if len(x)>1 and x.std()>0 and y.std()>0 else np.nan
    # The target coefficient in the actual prespecified design, not just
    # univariate moments; use the same source contrasts as production.
    predictors=MODELS["H1"][2]
    x=matrix(work,predictors)
    y=work.clarity_post.to_numpy(float)
    if np.linalg.matrix_rank(x)==x.shape[1] and work.motive_expression.std(ddof=0)>0:
        idx=1+predictors.index("motive_expression")
        out["H1:beta"]=float(np.linalg.lstsq(x,y,rcond=None)[0][idx]/work.motive_expression.std(ddof=0))
    else:
        out["H1:beta"]=np.nan
    return out


def screen(data,chains=8,sweeps=120,burn=40,seed=20261204,m=50):
    if chains<4 or sweeps-burn<20 or burn<0 or m<2:
        raise ValueError("Invalid trace design")
    traces=defaultdict(lambda:[[] for _ in range(chains)])
    def trace(chain,sweep,work,masks):
        if sweep>=burn:
            for k,v in scalar_summaries(work,masks).items():
                traces[k][chain].append(v)
    try:
        # Draw from the same implementation; retain only scalar diagnostics.
        for _ in draw_imputations(data,chains,sweeps,seed,trace=trace):
            pass
        results={k:diagnose(v) for k,v in traces.items()}
        terminal=[fit(work,"H1") for work,_ in draw_imputations(data,m,sweeps,seed+1)]
        pooled=pool(terminal)
    except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
        return dict(status="execution_failure",reason=str(exc),confirmatory_authorized=False)
    mcse=float(np.sqrt(pooled["between_variance"]/m))
    relative=mcse/pooled["se"]
    return dict(status="screen_pass" if results and all(x["status"]=="screen_pass" for x in results.values())
                and relative<=.10 else "screen_flag",diagnostics=results,
                chains=chains,sweeps=sweeps,burn=burn,m=m,seed=seed,
                pooled_beta=pooled["beta"],pooled_se=pooled["se"],
                terminal_mcse=mcse,mcse_to_se=relative,
                confirmatory_authorized=False,
                interpretation="scalar diagnostic screen, not proof of joint compatibility")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv")
    p.add_argument("--chains",type=int,default=8)
    p.add_argument("--sweeps",type=int,default=120)
    p.add_argument("--burn",type=int,default=40)
    p.add_argument("--m",type=int,default=50)
    p.add_argument("--seed",type=int,default=20261204)
    a=p.parse_args()
    if a.csv:
        data,_=prepare(read_records(a.csv))
    else:
        from imputation_calibration import raw_records,mask_and_stop
        from power import calibration
        from stress import generate
        rng=np.random.default_rng(a.seed)
        x,y=generate(rng,660,.6,calibration(.6,.15),True)
        data,_=mask_and_stop(rng,raw_records(x,y),"mixed_mar",500)
    print(json.dumps(screen(data,a.chains,a.sweeps,a.burn,a.seed,a.m),
                     indent=2,allow_nan=False))
