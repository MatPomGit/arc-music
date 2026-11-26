"""Synthetic comparison of two cluster sandwich corrections; no participant data."""
import argparse,json
import numpy as np
from scipy.stats import t
from bounded_simulation import bounded

def compare(g,x,y):
    _,g=np.unique(g,return_inverse=True)
    counts=np.bincount(g); keep=counts[g]>=2
    x,y,g=x[keep],y[keep],g[keep]
    _,g=np.unique(g,return_inverse=True); counts=np.bincount(g)
    G,N,p=len(counts),len(y),x.shape[1]
    if G<10 or N-G-p<=0: raise ValueError("Insufficient independent clusters")
    xm=np.zeros((G,p)); ym=np.zeros(G)
    np.add.at(xm,g,x); np.add.at(ym,g,y)
    x=x-xm[g]/counts[g,None]; y=y-ym[g]/counts[g]
    if np.linalg.matrix_rank(x)<p: raise ValueError("Rank deficient design")
    bread=np.linalg.inv(x.T@x); beta=bread@x.T@y; resid=y-x@beta
    scores=np.zeros((G,p)); np.add.at(scores,g,x*resid[:,None])
    base=bread@(scores.T@scores)@bread
    se=np.sqrt(base[0,0]*(G/(G-1))*((N-1)/(N-G-p)))
    nested=np.sqrt(base[0,0]*(G/(G-1))*((N-1)/(N-p)))
    return beta[0],se,nested,t.ppf(.975,G-1),G,N

def calibrate(seed=2606,reps=1000,reference_n=100000):
    if reps<1 or reference_n<100: raise ValueError("Invalid replication count")
    rng=np.random.default_rng(seed); cells=[]; refs=[]
    for beta in [0,.15,.3]:
        ref=compare(*bounded(rng,reference_n,6,beta))
        target=0.0 if beta==0 else float(ref[0])
        refs.append(dict(latent=beta,reference=float(ref[0]),se=float(ref[1]),target=target))
        for n in [80,160,240]:
            for scenario in ["mcar","mar","mnar"]:
                rows=[]; failures=0
                for _ in range(reps):
                    try: rows.append(compare(*bounded(rng,n,6,beta,.3,scenario)))
                    except (ValueError,np.linalg.LinAlgError): failures+=1
                if not rows: raise ValueError("All replications failed")
                b,s,sn,c,G,N=np.array(rows).T
                out=dict(latent=beta,n=n,scenario=scenario,target=target,
                         mean=float(b.mean()),bias=float((b-target).mean()),
                         mean_sessions=float(N.mean()),valid=len(rows),failures=failures)
                for name,ss in [("full",s),("nested",sn)]:
                    rate=float(np.mean(abs(b)>c*ss)); cov=float(np.mean(abs(b-target)<=c*ss))
                    out[name]=dict(rejection=rate,coverage=cov,
                        mcse_rejection=float(np.sqrt(rate*(1-rate)/len(rows))))
                cells.append(out)
    return dict(status="SYNTHETIC",seed=seed,reps=reps,reference_n=reference_n,references=refs,cells=cells)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--seed",type=int,default=2606)
    p.add_argument("--reps",type=int,default=1000)
    p.add_argument("--reference-n",type=int,default=100000)
    a=p.parse_args()
    print(json.dumps(calibrate(a.seed,a.reps,a.reference_n),indent=2,allow_nan=False))
