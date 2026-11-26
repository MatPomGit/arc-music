"""Prespecified H3--H5 validity contrasts. Development; no scale authorization."""
import numpy as np
from scipy.stats import rankdata

CONTRASTS=("H3_EXP_expression","H3_REF_clarity","H3_MOD_mood",
           "H4_PER_rumination","H4_AVO_avoidance","H5_EXP_specificity")

def domain_score(x,*,authorized=False):
    """Mean of retained items, at least 80% answered; never an overall score."""
    if not authorized:
        raise ValueError("frozen domain scoring not authorized")
    x=np.asarray(x,float)
    if x.ndim!=2 or x.shape[1]<3 or np.isinf(x).any() or not np.isin(x[np.isfinite(x)],np.arange(5)).all():
        raise ValueError("invalid ordinal domain matrix")
    count=np.isfinite(x).sum(axis=1)
    out=np.full(len(x),np.nan)
    ok=count>=np.ceil(.8*x.shape[1])
    out[ok]=np.nansum(x[ok],axis=1)/count[ok]
    return out

def _corr(a,b):
    a=a-a.mean(); b=b-b.mean()
    den=np.linalg.norm(a)*np.linalg.norm(b)
    if den<=1e-12:
        raise ValueError("constant rank variable")
    return float(np.clip(a@b/den,-1,1))

def effect(x,kind):
    ranks=np.apply_along_axis(rankdata,0,x)
    if kind=="spearman":
        return _corr(ranks[:,0],ranks[:,1])
    if kind=="partial":
        z=np.column_stack([np.ones(len(ranks)),ranks[:,2]])
        if np.linalg.matrix_rank(z)!=2:
            raise ValueError("constant baseline")
        residual=ranks[:,:2]-z@np.linalg.lstsq(z,ranks[:,:2],rcond=None)[0]
        return _corr(residual[:,0],residual[:,1])
    if kind=="paired_difference":
        return _corr(ranks[:,0],ranks[:,1])-_corr(ranks[:,0],ranks[:,2])
    raise ValueError("unknown contrast")

def bootstrap_test(columns,kind,reps=5000,seed=20261126,min_n=30):
    """Complete-pair/triple target; centered bootstrap two-sided test.

    Directional hypotheses require a positive point estimate as well as a
    Holm rejection. Percentile intervals are descriptive marginal intervals.
    Centered bootstrap p-values are asymptotic and need calibration.
    """
    x=np.column_stack(columns).astype(float)
    expected=2 if kind=="spearman" else 3
    if x.shape[1]!=expected or np.isinf(x).any() or reps<20 or min_n<30:
        raise ValueError("invalid contrast data or calibration settings")
    n_total=len(x); x=x[np.isfinite(x).all(axis=1)]
    if len(x)<min_n:
        return {"status":"unavailable","reason":"insufficient complete records","n":len(x),"n_total":n_total}
    try:
        estimate=effect(x,kind)
    except ValueError as exc:
        return {"status":"unavailable","reason":str(exc),"n":len(x),"n_total":n_total}
    rng=np.random.default_rng(seed); draws=[]; failures=0
    for _ in range(reps):
        try:
            draws.append(effect(x[rng.integers(len(x),size=len(x))],kind))
        except ValueError:
            failures+=1
    if failures>.05*reps:
        return {"status":"unavailable","reason":"bootstrap failures","n":len(x),"n_total":n_total,"failed":failures}
    draws=np.asarray(draws)
    # Ties count as at least as extreme. Add-one prevents zero Monte Carlo p.
    p=(1+np.sum(abs(draws-estimate)>=abs(estimate)))/(len(draws)+1)
    return {"status":"estimated","n":len(x),"n_total":n_total,"estimate":estimate,
            "interval":np.quantile(draws,[.025,.975]).tolist(),"p":float(p),
            "bootstrap_requested":reps,"bootstrap_failed":failures}

def holm(p):
    p=np.asarray(p,float)
    if p.ndim!=1 or not len(p) or not np.isfinite(p).all() or np.any((p<0)|(p>1)):
        raise ValueError("invalid p-values")
    order=np.argsort(p,kind="stable")
    adjusted=np.empty_like(p)
    adjusted[order]=np.minimum(1,np.maximum.accumulate((len(p)-np.arange(len(p)))*p[order]))
    return adjusted

def validity_family(scores,comparators,*,authorized=False,reps=5000,seed=20261126):
    """Freeze six contrast slots; unavailable comparator/domain retains p=1."""
    if not authorized:
        raise ValueError("confirmatory scoring and comparators not authorized")
    specs=[("EXP",("expression",),"spearman"),
           ("REF",("clarity_post","clarity_pre"),"partial"),
           ("MOD",("mood",),"spearman"),
           ("PER",("rumination",),"spearman"),
           ("AVO",("avoidance",),"spearman"),
           ("EXP",("expression","use_frequency"),"paired_difference")]
    rows={}
    for i,(name,(domain,keys,kind)) in enumerate(zip(CONTRASTS,specs)):
        if domain not in scores or any(k not in comparators for k in keys):
            row={"status":"unavailable","reason":"missing frozen domain or comparator"}
        else:
            row=bootstrap_test([scores[domain],*[comparators[k] for k in keys]],kind,reps,seed+i)
        rows[name]=row
    adj=holm([row.get("p",1.) for row in rows.values()])
    for row,p in zip(rows.values(),adj):
        row["holm_p"]=float(p)
        row["supports_directional_hypothesis"]=bool(row["status"]=="estimated" and p<=.05 and row["estimate"]>0)
    return rows
