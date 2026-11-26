"""Small ordinal FCS development calibration; not final MI validation."""
import argparse,json
import numpy as np
from missingness import simulate_selection
from ordinal_imputation import fit_multiple
from robust_cfa import robust_fit
from robust_calibration import wilson

def run(reps=8,m=5,sweeps=20,seed=20261126):
    rng=np.random.default_rng(seed); d=np.repeat(np.arange(2),3)
    truth=np.r_[np.full(6,.65),.35]; scenarios=[]
    for mechanism in ("MCAR","MAR","MNAR"):
        records=[]
        for i in range(reps):
            y,x,z,_=simulate_selection(400,2,3,.65,.35,mechanism,.25,rng)
            record={"replicate":i,"methods":{}}
            for name,delta in [("mi_mar",0.),("mi_mnar_minus1",-1.),("mi_mnar_plus1",1.)]:
                try:
                    f=fit_multiple(x,z,d,m=m,sweeps=sweeps,gibbs_steps=3,
                                   delta=delta,seed=seed+i)
                    pooled=f["pooled"]
                    if pooled is None:
                        record["methods"][name]={"status":"failure","failed_draws":f["failures"]}
                        continue
                    cover=(pooled["intervals"][:,0]<=truth)&(truth<=pooled["intervals"][:,1])
                    record["methods"][name]={"status":"proper","loading_bias":float(pooled["estimates"][0]-.65),
                          "correlation_bias":float(pooled["estimates"][-1]-.35),
                          "loading_covered":bool(cover[0]),"correlation_covered":bool(cover[-1]),
                          "average_coverage":float(cover.mean()),
                          "mean_missing_information_component":float(pooled["missing_information_component"].mean())}
                except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
                    record["methods"][name]={"status":"failure","reason":str(exc)}
            for name,data in [("full_data",y),("complete_case",x[np.isfinite(x).all(axis=1)])]:
                try:
                    f=robust_fit(data,d)
                    cover=(f.intervals[:,0]<=truth)&(truth<=f.intervals[:,1])
                    record["methods"][name]={"status":"proper","loading_bias":float(f.parameters[0]-.65),
                           "correlation_bias":float(f.parameters[-1]-.35),
                           "loading_covered":bool(cover[0]),"correlation_covered":bool(cover[-1]),
                           "average_coverage":float(cover.mean())}
                except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
                    record["methods"][name]={"status":"failure","reason":str(exc)}
            records.append(record)
        summary={}
        for name in records[0]["methods"]:
            good=[r["methods"][name] for r in records if r["methods"][name]["status"]=="proper"]
            covered=sum(r["loading_covered"] for r in good)
            summary[name]={"proper":len(good),"proper_interval":wilson(len(good),reps),
                           "loading_coverage_unconditional":covered/reps,
                           "loading_coverage_conditional":covered/len(good) if good else None,
                           "loading_coverage_interval":wilson(covered,len(good)) if good else None,
                           "loading_bias":float(np.mean([r["loading_bias"] for r in good])) if good else None,
                           "correlation_bias":float(np.mean([r["correlation_bias"] for r in good])) if good else None}
        scenarios.append({"mechanism":mechanism,"requested":reps,"summary":summary,"records":records})
    return {"label":"SYNTHETIC DEVELOPMENT ONLY; FCS compatibility and convergence not validated",
            "seed":seed,"imputations":m,"sweeps":sweeps,"scenarios":scenarios}

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--reps",type=int,default=8)
    p.add_argument("--m",type=int,default=5); p.add_argument("--sweeps",type=int,default=20)
    a=p.parse_args()
    if a.reps<1 or a.m<2 or a.sweeps<1: p.error("invalid calibration design")
    print(json.dumps(run(a.reps,a.m,a.sweeps),indent=2,allow_nan=False))
