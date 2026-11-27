"""End-to-end P06 analysis from a frozen flat session log."""
import argparse,json
import pandas as pd
from ledger import ledger,flow_counts
from inference import fit_arrays,PREDICTORS
from secondary import secondary
from sensitivity import cluster_bootstrap
from daily import daily_ledger,summarize
from robustness import robustness
from withdrawal_audit import audit

def analyze(frame,reps=499,seed=2606,enrollment=None,checkins=None,*,data_kind="synthetic"):
    if data_kind not in ("synthetic","empirical"):
        raise ValueError("Explicit valid data kind required")
    audit_result=audit(enrollment,checkins,frame) if data_kind=="empirical" else None
    if (enrollment is None)!=(checkins is None):
        raise ValueError("Supply both enrollment and daily check-ins")
    d=ledger(frame)
    daily=summarize(daily_ledger(enrollment,checkins,d)) if enrollment is not None else None
    a=d[d.session_status.eq("eligible")].copy()
    complete=a.dropna(subset=["interference"])
    result={"data_kind":data_kind,"confirmatory_authorized":False,"withdrawal_audit":audit_result,"flow":flow_counts(d),"primary":fit_arrays(complete.participant_id,
             complete[PREDICTORS],complete.interference)}
    narrow=ledger(frame,upper_hours=26)
    n=narrow.loc[narrow.session_status.eq("eligible")].dropna(subset=["interference"])
    result["timing_sensitivity"]={"window_hours":[24,26],"flow":flow_counts(narrow)}
    try:
        result["timing_sensitivity"]["estimate"]=fit_arrays(n.participant_id,n[PREDICTORS],n.interference)
        result["timing_sensitivity"]["same_complete_sessions"]=set(n.session_id)==set(complete.session_id)
    except (ValueError,ArithmeticError) as exc:
        result["timing_sensitivity"]["unavailable"]=str(exc)
    result["robustness"]=robustness(d)
    if enrollment is not None:
        result["daily_denominators"]=daily
    else:
        result["daily_denominators_unavailable"]="Enrollment and check-in logs not supplied"
    # Optional secondary outcomes cannot silently suppress the primary result.
    try:
        result["secondary"]=secondary(complete)
    except (ValueError,KeyError) as exc:
        result["secondary_unavailable"]=str(exc)
    result["primary_target_status"]="descriptive_observed_defined_only" if not a.endpoint_state.eq("defined").all() else "defined_logged_sessions"
    if not a.endpoint_state.eq("defined").all():
        result["missingness_unavailable"]="Undefined or unascertained endpoint states; full-session estimand not identified. No numerical imputation."
    elif a.interference.isna().any():
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
    p.add_argument("--data-kind",choices=["synthetic","empirical"],required=True)
    p.add_argument("--enrollment")
    p.add_argument("--checkins")
    a=p.parse_args()
    if a.bootstrap<1:p.error("bootstrap must be positive")
    d=pd.read_csv(a.csv,dtype={"participant_id":str,"session_id":str})
    if bool(a.enrollment)!=bool(a.checkins):p.error("Supply both --enrollment and --checkins")
    if a.data_kind=="empirical" and not a.enrollment:p.error("Empirical mode requires both ledgers")
    e=pd.read_csv(a.enrollment,dtype={"participant_id":str}) if a.enrollment else None
    c=pd.read_csv(a.checkins,dtype={"participant_id":str}) if a.checkins else None
    print(json.dumps(analyze(d,a.bootstrap,a.seed,e,c,data_kind=a.data_kind),indent=2,allow_nan=False))
