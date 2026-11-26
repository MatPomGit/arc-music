"""Paired synthetic comparison of interval coverage and width."""
import argparse,json
import numpy as np
from recovery import simulate
from robust_cfa import robust_fit
from correlation_intervals import compare_intervals
from robust_calibration import wilson

def run(reps=8,boot=99,seed=20261126):
    d=np.repeat(np.arange(2),4); out=[]
    for sid,(n,rho) in enumerate([(250,.35),(500,.35),(500,.80)]):
        rows=[]
        for i in range(reps):
            a,b=np.random.SeedSequence([seed,sid,i]).spawn(2)
            x=simulate(n,2,4,.65,rho,False,0.,np.random.default_rng(a))
            try:
                f=robust_fit(x,d)
                result=compare_intervals(x,d,reps=boot,seed=int(b.generate_state(1)[0]),fit=f)
                rows.append({"replicate":i,"status":"proper",**result})
            except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
                rows.append({"replicate":i,"status":"failure","reason":str(exc)})
        summary={}
        for name in ("wald","fisher_delta","percentile","basic"):
            vals=[r[name][0] for r in rows if r["status"]=="proper" and r[name] is not None]
            covered=sum(lo<=rho<=hi for lo,hi in vals)
            summary[name]={"available":len(vals),"covered":covered,
                "coverage_unconditional":covered/reps,"coverage_conditional":covered/len(vals) if vals else None,
                "coverage_interval":wilson(covered,len(vals)) if vals else None,
                "mean_width":float(np.mean([hi-lo for lo,hi in vals])) if vals else None}
        out.append({"n":n,"rho":rho,"requested":reps,"bootstrap":boot,"methods":summary,"records":rows})
    return {"label":"SYNTHETIC DEVELOPMENT; paired alternatives, no method approved",
            "seed":seed,"scenarios":out}
if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--reps",type=int,default=8)
    p.add_argument("--boot",type=int,default=99); a=p.parse_args()
    if a.reps<1 or a.boot<20: p.error("invalid replication design")
    print(json.dumps(run(a.reps,a.boot),indent=2,allow_nan=False))
