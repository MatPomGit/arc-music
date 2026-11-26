"""Synthetic comparison of selection sensitivity; no participant data."""
import argparse,json
import numpy as np
from missingness import simulate_selection,selection_fit
from ordinal_cfa import fit_cfa
from robust_calibration import wilson

def run(reps=30,seed=20261129):
    rng=np.random.default_rng(seed); output=[]
    d=np.repeat(np.arange(2),4)
    for mechanism in ("MCAR","MAR","MNAR"):
        records=[]
        for i in range(reps):
            y,x,z,prob=simulate_selection(500,2,4,.65,.35,mechanism,.25,rng)
            c=np.isfinite(x).all(axis=1)
            row={"replicate":i,"complete_n":int(c.sum()),"methods":{}}
            methods={"full_data":lambda:fit_cfa(y,d),
                     "complete_case":lambda:fit_cfa(x[c],d),
                     "ipw_mar":lambda:selection_fit(x,z,d),
                     "oracle_ipw":lambda:selection_fit(x,z,d,prob=prob),
                     "tilt_minus2":lambda:selection_fit(x,z,d,delta=-2),
                     "tilt_plus2":lambda:selection_fit(x,z,d,delta=2)}
            for name,method in methods.items():
                try:
                    result=method(); f=getattr(result,"fit",result)
                    if not f.proper:
                        raise ArithmeticError("improper CFA")
                    row["methods"][name]={"status":"proper","first_loading_bias":float(f.loadings[0]-.65),
                       "correlation_bias":float(f.phi[0,1]-.35),
                       "threshold_bias":float(f.thresholds[0,1]+.25),
                       "ess":float(getattr(result,"ess",len(y) if name=="full_data" else c.sum()))}
                except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
                    row["methods"][name]={"status":"failure","reason":str(exc)}
            records.append(row)
        summary={}
        for name in methods:
            good=[row["methods"][name] for row in records if row["methods"][name]["status"]=="proper"]
            summary[name]={"proper":len(good),"proper_interval":wilson(len(good),reps)}
            for field in ("first_loading_bias","correlation_bias","threshold_bias","ess"):
                summary[name][field]=float(np.mean([a[field] for a in good])) if good else None
        output.append({"mechanism":mechanism,"requested":reps,"summary":summary,"records":records})
    return {"label":"SYNTHETIC DEVELOPMENT ONLY; oracle unavailable in empirical research","seed":seed,"scenarios":output}

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--reps",type=int,default=30)
    a=p.parse_args()
    if a.reps<1: p.error("positive replication count required")
    print(json.dumps(run(a.reps),indent=2,allow_nan=False))
