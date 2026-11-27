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
    # Missing optional columns make affected hypotheses unavailable, not a
    # malformed required schema. Malformed supplied values fail closed.
    import pandas as pd
    required={"participant_id","interference",*PREDICTORS}
    if not required<=set(d):
        raise ValueError("Missing required secondary design fields")
    d=d.copy()
    for c in ["distress_post","brooding"]:
        if c not in d:
            d[c]=np.nan
        else:
            d[c]=pd.to_numeric(d[c],errors="raise")
            v=d[c].dropna()
            if not (v.between(0,10)&(v%1==0)).all():
                raise ValueError("Invalid post score")
    d["relief"]=d.distress_pre-d.distress_post
    a=d.dropna(subset=["relief"]).copy()
    a["avoidance_w"]=a.avoidance-a.groupby("participant_id").avoidance.transform("mean")
    a["relief_w"]=a.relief-a.groupby("participant_id").relief.transform("mean")
    a["interaction"]=a.avoidance_w*a.relief_w
    names=PREDICTORS+["relief_w","interaction"]
    b=d.dropna(subset=["relief","brooding"])
    def attempt(frame,predictors):
        try:
            return fit_arrays(frame.participant_id,frame[predictors],frame.interference),None
        except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
            return None,str(exc)
    r,re=attempt(a,names)
    s,se=attempt(b,PREDICTORS+["relief","brooding"])
    rows=[]
    for label,result,index,reason in [("relief",r,4,re),("avoidance_x_relief",r,5,re),("brooding",s,5,se)]:
        if result is None:
            rows.append({"term":label,"available":False,"reason":reason,"p":None,"p_holm":None})
        else:
            rows.append(dict(term=label,available=True,participants=result["participants"],
                             sessions=result["sessions"],**{k:result[k][index] for k in ["estimate","se","ci_low","ci_high","p"]}))
    for row,p in zip(rows,holm([r["p"] if r["available"] else 1. for r in rows])):
        if row["available"]:
            row["p_holm"]=float(p)
    return rows
