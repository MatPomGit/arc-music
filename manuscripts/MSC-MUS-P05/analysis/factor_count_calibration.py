"""Synthetic EFA recovery with factor number selected from the observed data."""
import argparse,json
import numpy as np
from ordinal_efa import parallel_analysis,polychoric_matrix,minres_promax
from recovery import simulate,recover
from robust_calibration import wilson

def assess(x,true_k,items,loading,pa_reps=500,seed=20261126):
    complete=x[np.isfinite(x).all(axis=1)]
    row={"complete_n":len(complete),"selected":None,"proper":False,
         "correct_count":False,"joint_recovery":False}
    try:
        pa=parallel_analysis(complete,pa_reps,seed)
        row.update(selected=int(pa.retained),correct_count=bool(pa.retained==true_k),
                   observed=pa.observed.tolist(),null95=pa.reference.tolist())
        if pa.retained==0:
            row.update(status="no_factor"); return row
        fit=minres_promax(polychoric_matrix(complete),pa.retained)
        row.update(status="near_heywood" if fit.near_heywood else "proper",
                   proper=not fit.near_heywood,rms_residual=fit.rms_residual)
        if pa.retained==true_k and not fit.near_heywood:
            avg,accuracy=recover(fit.pattern,true_k,items)
            row.update(loading_bias=avg-loading,assignment_accuracy=accuracy,
                       joint_recovery=bool(accuracy>=.90 and abs(avg-loading)<=.05))
    except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
        row.update(status="failure",reason=str(exc))
    return row

def run(n=400,k=7,items=5,loading=.65,rho=.35,skew=False,missing=0.,
        reps=10,pa_reps=500,seed=20261126,offset=0):
    if reps<1 or offset<0 or pa_reps<10:
        raise ValueError("invalid calibration design")
    rows=[]
    for i in range(offset,offset+reps):
        a,b=np.random.SeedSequence([seed,i]).spawn(2)
        x=simulate(n,k,items,loading,rho,skew,missing,np.random.default_rng(a))
        rows.append({"replicate":i,**assess(x,k,items,loading,pa_reps,int(b.generate_state(1)[0]))})
    counts={}
    for row in rows:
        key=str(row["selected"]) if row["selected"] is not None else "unavailable"
        counts[key]=counts.get(key,0)+1
    correct=sum(r["correct_count"] for r in rows)
    proper=sum(r["proper"] for r in rows)
    joint=sum(r["joint_recovery"] for r in rows)
    return {"label":"SYNTHETIC DEVELOPMENT; no true count supplied to extraction",
            "protocol_permutations":pa_reps==500,"seed":seed,"offset":offset,
            "n":n,"factors":k,"items_per_factor":items,"loading":loading,"rho":rho,
            "skew":skew,"missing":missing,"requested":reps,"pa_reps":pa_reps,
            "selected_counts":counts,"correct_count":correct,"correct_interval":wilson(correct,reps),
            "proper":proper,"joint_recovery":joint,"joint_interval":wilson(joint,reps),"records":rows}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--n",type=int,default=400); p.add_argument("--k",type=int,default=7)
    p.add_argument("--items",type=int,default=5); p.add_argument("--loading",type=float,default=.65)
    p.add_argument("--rho",type=float,default=.35); p.add_argument("--skew",action="store_true")
    p.add_argument("--missing",type=float,default=0.); p.add_argument("--reps",type=int,default=10)
    p.add_argument("--pa-reps",type=int,default=500); p.add_argument("--seed",type=int,default=20261126)
    p.add_argument("--offset",type=int,default=0); a=p.parse_args()
    print(json.dumps(run(a.n,a.k,a.items,a.loading,a.rho,a.skew,a.missing,
                         a.reps,a.pa_reps,a.seed,a.offset),indent=2,allow_nan=False))
