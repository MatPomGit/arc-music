"""Small synthetic calibration, with unconditional accounting for failures."""
import argparse,json
import numpy as np
from scipy.stats import norm
from recovery import simulate
from robust_cfa import robust_fit

def wilson(success,total):
    z=norm.ppf(.975); p=success/total; d=1+z*z/total
    c=(p+z*z/(2*total))/d; h=z*np.sqrt(p*(1-p)/total+z*z/(4*total**2))/d
    return [max(0.,float(c-h)),min(1.,float(c+h))]

def run(reps=30,full_reps=3,seed=20261128):
    rng=np.random.default_rng(seed)
    out=[]
    for n,k,items,loading,rho,skew,missing,count in [
        (500,2,4,.65,.35,False,0.,reps),
        (500,2,4,.40,.80,True,0.,reps),
        (500,7,5,.65,.35,False,0.,full_reps),
        (500,7,5,.65,.35,True,.02,full_reps)]:
        d=np.repeat(np.arange(k),items)
        truth=np.r_[np.full(k*items,loading),np.full(k*(k-1)//2,rho)]
        records=[]
        for i in range(count):
            x=simulate(n,k,items,loading,rho,skew,missing,rng)
            x=x[np.isfinite(x).all(axis=1)]
            record={"replicate":i,"complete_n":len(x)}
            try:
                f=robust_fit(x,d)
                cover=(f.intervals[:,0]<=truth)&(truth<=f.intervals[:,1])
                record.update(status="proper",first_loading_covered=bool(cover[0]),
                    first_correlation_covered=bool(cover[k*items]),
                    average_coverage=float(cover.mean()),
                    first_loading_bias=float(f.parameters[0]-loading),
                    rejected=bool(f.p_value<.05),p_value=f.p_value,
                    effective_df=f.effective_df,nominal_df=f.nominal_df)
            except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
                record.update(status="failure",reason=str(exc))
            records.append(record)
        good=[a for a in records if a["status"]=="proper"]
        g=len(good)
        covered=sum(a["first_loading_covered"] for a in good)
        corr_covered=sum(a["first_correlation_covered"] for a in good)
        rejected=sum(a["rejected"] for a in good)
        out.append({"n":n,"factors":k,"items":k*items,"loading":loading,"rho":rho,
                    "skew":skew,"missing_mcar_per_item":missing,"requested":count,"proper":g,
                    "proper_rate_interval":wilson(g,count),
                    "loading_coverage_unconditional":covered/count,
                    "loading_coverage_conditional":covered/g if g else None,
                    "loading_coverage_conditional_interval":wilson(covered,g) if g else None,
                    "correlation_coverage_unconditional":corr_covered/count,
                    "rejection_conditional":rejected/g if g else None,
                    "rejection_conditional_interval":wilson(rejected,g) if g else None,
                    "records":records})
    return {"label":"SYNTHETIC DEVELOPMENT ONLY; not final WLSMV calibration","seed":seed,"scenarios":out}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--reps",type=int,default=30)
    p.add_argument("--full-reps",type=int,default=3)
    a=p.parse_args()
    if min(a.reps,a.full_reps)<1: p.error("positive replication counts required")
    print(json.dumps(run(a.reps,a.full_reps),indent=2,allow_nan=False))
