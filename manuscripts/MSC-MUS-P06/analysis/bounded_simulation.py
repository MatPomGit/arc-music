"""Calibrate observed-scale slope using a separate large synthetic reference."""
import argparse,json
import numpy as np
from scipy.special import expit
from scipy.optimize import brentq
from inference import fit_arrays
from simulation import draw

def bounded(rng,n,m,beta,missing=0,scenario="mar"):
    g,x,y=draw(rng,n,m,beta,missing=0)
    y=np.clip(np.rint(y),0,10)
    if not missing: return g,x,y
    score=np.zeros(len(y)) if scenario=="mcar" else .25*(x[:,1]-5)+.1*(x[:,0]-5)
    if scenario=="mnar": score=score+.35*(y-5)
    z=brentq(lambda z:expit(z+score).mean()-missing,-40,40)
    keep=rng.random(len(y))>=expit(z+score)
    return g[keep],x[keep],y[keep]

def calibrate(seed=2606,reps=1000,reference_n=100000,*,design=None):
    if reps<1 or reference_n<100: raise ValueError("Invalid calibration size")
    rng=np.random.default_rng(seed)
    cells=[]
    if design is not None:
        n,beta,missing,scenario=design
        if n<40 or not -.6<=beta<=.6 or not 0<=missing<=.9 or scenario not in ('mcar','mar','mnar'):raise ValueError('Invalid design')
    for beta in ([0,.15,.3] if design is None else [design[1]]):
        # Finite Monte Carlo reference, not exact population truth.
        ref=fit_arrays(*bounded(rng,reference_n,6,beta))
        target=ref["estimate"][0]
        for n in ([80,160,240] if design is None else [design[0]]):
            for scenario in (["mar","mnar"] if design is None else [design[3]]):
                vals=[]; failed=0
                for _ in range(reps):
                    try: vals.append(fit_arrays(*bounded(rng,n,6,beta,.3 if design is None else design[2],scenario)))
                    except (ValueError,np.linalg.LinAlgError): failed+=1
                v=len(vals)
                reject=np.mean([r["p"][0]<.05 for r in vals]) if v else None
                cells.append({"latent_slope":beta,"reference_slope":target,
                  "reference_se":ref["se"][0],"n":n,"missing":.3 if design is None else design[2],"scenario":scenario,"valid":v,"failed":failed,
                  "rejection_rate":float(reject) if v else None,
                  "rejection_mcse":float(np.sqrt(reject*(1-reject)/v)) if v else None,
                  "coverage_reference":float(np.mean([r["ci_low"][0]<=target<=r["ci_high"][0] for r in vals])) if v else None,
                  "bias_reference":float(np.mean([r["estimate"][0] for r in vals])-target) if v else None})
    return {"status":"SYNTHETIC_BOUNDED","seed":seed,"reference_n":reference_n,"reps":reps,"cells":cells}
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--reps",type=int,default=1000)
    p.add_argument("--reference-n",type=int,default=100000)
    p.add_argument("--seed",type=int,default=2606)
    p.add_argument('--design',nargs=4)
    a=p.parse_args()
    design=None if a.design is None else (int(a.design[0]),float(a.design[1]),float(a.design[2]),a.design[3])
    print(json.dumps(calibrate(a.seed,a.reps,a.reference_n,design=design),indent=2,allow_nan=False))
