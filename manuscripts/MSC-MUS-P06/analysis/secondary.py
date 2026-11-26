"""Predeclared secondary associations and Holm correction."""
import numpy as np
from inference import PREDICTORS, fit_arrays

def holm(p):
    p=np.asarray(p,float)
    if not np.isfinite(p).all() or not ((p>=0)&(p<=1)).all():
        raise ValueError("Invalid p values")
    order=np.argsort(p)
    adjusted=np.empty_like(p)
    adjusted[order]=np.minimum(1,np.maximum.accumulate(p[order]*(len(p)-np.arange(len(p)))))
    return adjusted

def secondary(d):
    # d must come from primary eligible_rows; post scores are separately validated.
    import pandas as pd
    d=d.copy()
    for c in ["distress_post","brooding"]:
        d[c]=pd.to_numeric(d[c],errors="raise")
        v=d[c].dropna()
        if not (v.between(0,10)&(v%1==0)).all(): raise ValueError("Invalid post score")
    d["relief"]=d.distress_pre-d.distress_post
    a=d.dropna(subset=["relief"]).copy()
    a["avoidance_w"]=a.avoidance-a.groupby("participant_id").avoidance.transform("mean")
    a["relief_w"]=a.relief-a.groupby("participant_id").relief.transform("mean")
    a["interaction"]=a.avoidance_w*a.relief_w
    names=PREDICTORS+["relief_w","interaction"]
    r=fit_arrays(a.participant_id,a[names],a.interference)
    b=d.dropna(subset=["relief","brooding"])
    s=fit_arrays(b.participant_id,b[PREDICTORS+["relief","brooding"]],b.interference)
    rows=[]
    for label,result,index in [("relief",r,4),("avoidance_x_relief",r,5),("brooding",s,5)]:
        rows.append(dict(term=label,participants=result["participants"],sessions=result["sessions"],
                         **{k:result[k][index] for k in ["estimate","se","ci_low","ci_high","p"]}))
    for row,p in zip(rows,holm([r["p"] for r in rows])):
        row["p_holm"]=float(p)
    return rows
