"""End-to-end P06 analysis from a frozen flat session log."""
import argparse,json
import pandas as pd
from ledger import ledger,flow_counts
from inference import fit_arrays,PREDICTORS
from secondary import secondary
from sensitivity import cluster_bootstrap

def analyze(frame,reps=499,seed=2606):
    d=ledger(frame)
    a=d[d.session_status.eq("eligible")].copy()
    complete=a.dropna(subset=["interference"])
    result={"flow":flow_counts(d),"primary":fit_arrays(complete.participant_id,
             complete[PREDICTORS],complete.interference)}
    # Optional secondary outcomes cannot silently suppress the primary result.
    try:
        result["secondary"]=secondary(complete)
    except (ValueError,KeyError) as exc:
        result["secondary_unavailable"]=str(exc)
    if a.interference.isna().any():
        try:
            result["missingness"]=cluster_bootstrap(a,reps=reps,seed=seed)
        except (ValueError,ArithmeticError) as exc:
            result["missingness_unavailable"]=str(exc)
    else:
        result["missingness_unavailable"]="No missing outcomes among eligible logged sessions"
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--bootstrap",type=int,default=499)
    p.add_argument("--seed",type=int,default=2606)
    a=p.parse_args()
    if a.bootstrap<1:p.error("bootstrap must be positive")
    d=pd.read_csv(a.csv,dtype={"participant_id":str,"session_id":str})
    print(json.dumps(analyze(d,a.bootstrap,a.seed),indent=2,allow_nan=False))
