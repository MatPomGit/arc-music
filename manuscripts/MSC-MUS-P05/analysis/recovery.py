"""Synthetic development calibration. Not a validation or final sample-size study."""
import argparse
import json
import numpy as np
from scipy.optimize import linear_sum_assignment
from ordinal_efa import polychoric_matrix, minres_promax, parallel_analysis

def simulate(n,k,items,loading,rho,skew,missing,rng):
    if not (n>=30 and k>=2 and items>=3 and 0<loading<1 and 0<=rho<1 and 0<=missing<1):
        raise ValueError("invalid simulation parameters")
    phi = np.full((k,k),rho)
    np.fill_diagonal(phi,1.)
    latent = rng.multivariate_normal(np.zeros(k),phi,size=n)
    z = loading*np.repeat(latent,items,axis=1) + np.sqrt(1-loading**2)*rng.normal(size=(n,k*items))
    cuts = [-.85,-.25,.25,.85] if not skew else [-.2,.35,.85,1.35]
    x = np.digitize(z,cuts).astype(float)
    if missing:
        x[rng.random(x.shape)<missing] = np.nan
    return x

def recover(pattern,k,items):
    """Align columns/signs by maximum absolute domain-average loading."""
    means = pattern.reshape(k,items,k).mean(axis=1)
    row,col = linear_sum_assignment(-np.abs(means))
    ordered = pattern[:,col]*np.sign(means[row,col])
    expected = np.repeat(np.arange(k),items)
    primary = ordered[np.arange(k*items),expected]
    assignment = np.argmax(np.abs(ordered),axis=1)
    return float(np.mean(primary)), float(np.mean(assignment==expected))

def run(n=400,k=3,items=3,loading=.65,rho=.35,skew=False,missing=0.,reps=12,seed=20261126,pa_reps=0):
    rng = np.random.default_rng(seed)
    records = []
    for i in range(reps):
        x = simulate(n,k,items,loading,rho,skew,missing,rng)
        complete = x[np.isfinite(x).all(axis=1)]
        record = {"replicate":i,"complete_n":len(complete)}
        try:
            r = polychoric_matrix(complete)
            fit = minres_promax(r,k)
            avg,accuracy = recover(fit.pattern,k,items)
            record.update(status="ok",loading_bias=avg-loading,assignment_accuracy=accuracy,
                          near_heywood=fit.near_heywood,rms_residual=fit.rms_residual,
                          min_eigenvalue=fit.min_eigenvalue)
            if pa_reps:
                result = parallel_analysis(complete,pa_reps,seed+i)
                record["pa_retained"] = result.retained
        except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
            record.update(status="failure",reason=str(exc))
        records.append(record)
    good = [r for r in records if r["status"]=="ok"]
    proper = [r for r in good if not r["near_heywood"]]
    return {"label":"SYNTHETIC DEVELOPMENT ONLY","seed":seed,"n":n,"factors":k,
            "items_per_factor":items,"loading":loading,"factor_correlation":rho,
            "skew":skew,"missing_mcar_per_item":missing,"replicates":reps,
            "pa_replicates":pa_reps,"proper_fits":len(proper),"failed_fits":reps-len(good),
            "mean_loading_bias":float(np.mean([r["loading_bias"] for r in proper])) if proper else None,
            "mean_assignment_accuracy":float(np.mean([r["assignment_accuracy"] for r in proper])) if proper else None,
            "records":records}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--reps",type=int,default=12)
    parser.add_argument("--pa-reps",type=int,default=0)
    parser.add_argument("--full-pool",action="store_true")
    args=parser.parse_args()
    k,items=(7,5) if args.full_pool else (3,3)
    scenarios=[run(n=n,k=k,items=items,loading=l,rho=r,skew=s,missing=m,reps=args.reps,
                   seed=20261126+i,pa_reps=args.pa_reps)
               for i,(n,l,r,s,m) in enumerate([(400,.65,.35,False,0.),(500,.65,.35,True,.02),
                                               (400,.40,.80,True,0.)])]
    print(json.dumps(scenarios,indent=2,allow_nan=False))
