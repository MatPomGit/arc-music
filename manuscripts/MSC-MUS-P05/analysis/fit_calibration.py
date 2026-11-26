"""Paired correctly specified and collapsed CFA diagnostics on synthetic data."""
import argparse,json
import numpy as np
from recovery import simulate
from robust_cfa import robust_fit
from fit_diagnostics import from_fit

def run(reps=30,seed=20261126):
    rng=np.random.default_rng(seed); scenarios=[]
    for n,rho in [(250,.35),(500,.35),(500,.8)]:
        records=[]
        for i in range(reps):
            x=simulate(n,2,4,.65,rho,False,0.,rng)
            row={"replicate":i,"models":{}}
            for name,d in [("two_factor",np.repeat(np.arange(2),4)),("one_factor",np.zeros(8,int))]:
                try:
                    row["models"][name]={"status":"proper",**from_fit(robust_fit(x,d))}
                except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
                    row["models"][name]={"status":"failure","reason":str(exc)}
            records.append(row)
        scenarios.append({"n":n,"rho":rho,"requested":reps,"records":records})
    return {"label":"SYNTHETIC DEVELOPMENT; indices are nonstandard and not validated WLSMV",
            "seed":seed,"scenarios":scenarios}

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--reps",type=int,default=30)
    a=p.parse_args()
    if a.reps<1: p.error("positive replication count required")
    print(json.dumps(run(a.reps),indent=2,allow_nan=False))
