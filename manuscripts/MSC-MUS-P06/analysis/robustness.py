"""Prespecified descriptive session-overlap and technical-failure sensitivities."""
import pandas as pd
import numpy as np
from inference import fit_arrays,PREDICTORS

def context_flags(d):
    # All logged starts, including non-primary sessions, contribute context.
    out=d.copy()
    out["prior_start_24h"]=False
    out["later_start_during_endpoint"]=False
    for _,g in out.groupby("participant_id"):
        starts=g.start_time.dropna().sort_values()
        for idx,r in g.iterrows():
            if pd.isna(r.start_time) or pd.isna(r.end_time): continue
            other=starts.drop(index=idx,errors="ignore")
            out.loc[idx,"prior_start_24h"]=bool(((other>=r.start_time-pd.Timedelta(hours=24))&(other<r.start_time)).any())
            out.loc[idx,"later_start_during_endpoint"]=bool(((other>=r.end_time)&(other<r.end_time+pd.Timedelta(hours=24))).any())
    return out

def robustness(d):
    d=context_flags(d)
    a=d.loc[d.session_status.eq("eligible") & d.interference.notna()]
    masks={"no_prior_logged_start":~a.prior_start_24h,
           "no_later_logged_start":~a.later_start_during_endpoint,
           "no_prior_or_later_logged_start":~a.prior_start_24h & ~a.later_start_during_endpoint}
    if "technical_failure" in a:
        v=a.technical_failure
        if not v.dropna().map(lambda x:isinstance(x,(bool,np.bool_))).all():
            raise ValueError("Invalid technical failure flag")
        masks["confirmed_no_technical_failure"]=v.map(lambda x:pd.notna(x) and not bool(x))
    result={}
    for name,mask in masks.items():
        b=a.loc[mask]
        row={"sessions_before_singleton_filter":len(b),"excluded_sessions":len(a)-len(b)}
        try:
            row["estimate"]=fit_arrays(b.participant_id,b[PREDICTORS],b.interference)
        except (ValueError,np.linalg.LinAlgError) as exc:
            row["unavailable"]=str(exc)
        result[name]=row
    if "technical_failure" not in a:
        result["confirmed_no_technical_failure"]={"unavailable":"Technical failure field absent"}
    return {"interpretation":"Descriptive subset comparisons; later starts and technical failures are post-exposure selection, not confounder adjustment. Unlogged starts are unknown.","models":result}
