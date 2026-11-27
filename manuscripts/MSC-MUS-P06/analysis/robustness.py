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
    try: confounding=confounding_grid(a)
    except (ValueError,np.linalg.LinAlgError) as exc:confounding={"unavailable":str(exc)}
    return {"hypothetical_confounding":confounding,"interpretation":"Descriptive subset comparisons; later starts and technical failures are post-exposure selection, not confounder adjustment. Unlogged starts are unknown.","models":result}


def confounding_grid(a):
    """Hypothetical omitted-variable coefficient change, not causal inference."""
    g=a.participant_id.to_numpy()
    x=a[PREDICTORS].to_numpy(float)
    y=a.interference.to_numpy(float)
    _,idx=np.unique(g,return_inverse=True)
    count=np.bincount(idx);keep=count[idx]>=2
    g,x,y=g[keep],x[keep],y[keep]
    _,idx=np.unique(g,return_inverse=True);count=np.bincount(idx)
    if len(count)<10:
        raise ValueError("Too few participants for confounding diagnostic")
    z=np.column_stack([x,y])
    mean=np.zeros((len(count),z.shape[1]))
    np.add.at(mean,idx,z)
    z=z-mean[idx]/count[idx,None]
    x,y=z[:,:-1],z[:,-1]
    if np.linalg.matrix_rank(x)<x.shape[1]:
        raise ValueError("Rank deficient diagnostic design")
    beta=np.linalg.lstsq(x,y,rcond=None)[0]
    ry=y-x@beta
    rx=x[:,0]-x[:,1:]@np.linalg.lstsq(x[:,1:],x[:,0],rcond=None)[0]
    if np.linalg.norm(rx)<=0 or np.linalg.norm(ry)<=0:
        raise ValueError("Degenerate residual variation")
    scale=np.linalg.norm(ry)/np.linalg.norm(rx)
    grid=[]
    for r2x in (.01,.05,.10,.20):
        for r2y in (.01,.05,.10,.20):
            magnitude=float(scale*np.sqrt(r2y*r2x/(1-r2x)))
            grid.append({"partial_r2_avoidance":r2x,"partial_r2_interference":r2y,
                         "absolute_coefficient_change":magnitude,
                         "hypothetical_lower":float(beta[0]-magnitude),
                         "hypothetical_upper":float(beta[0]+magnitude)})
    return {"observed_coefficient":float(beta[0]),"participants":len(count),
            "sessions":len(y),"grid":grid,"not_confidence_intervals":True,
            "interpretation":"Single hypothetical within-person omitted variable; no causal correction."}
