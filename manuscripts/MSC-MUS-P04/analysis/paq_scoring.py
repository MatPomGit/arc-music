"""PAQ-S-PL numeric total scoring; no item wording or participant records."""
import numpy as np

def validate_items(items):
    raw=np.asarray(items)
    if raw.ndim!=2 or raw.shape[1]!=6 or raw.dtype.kind not in "iuf":
        raise ValueError("Expected numeric N x 6 PAQ-S responses")
    x=raw.astype(float)
    v=x[np.isfinite(x)]
    if np.isinf(x).any() or np.any((v<1)|(v>7)|(v!=np.floor(v))):
        raise ValueError("Responses must be integers 1 to 7 or NaN")
    return x

def validate_total(values, required=True):
    v=np.asarray(values,float)
    if v.ndim!=1 or np.isinf(v).any() or (required and np.isnan(v).any()):
        raise ValueError("Invalid PAQ-S totals")
    observed=v[np.isfinite(v)]
    if np.any((observed<6)|(observed>42)|(observed!=np.floor(observed))):
        raise ValueError("PAQ-S total must be integer 6 to 42")
    return v

def score(items):
    x=validate_items(items)
    total=x.sum(axis=1)
    return {"total":total,"paq_baseline_eligible":np.isfinite(total)}

def describe_scores(values):
    x=validate_total(values,required=False)
    v=x[np.isfinite(x)]; n=len(v)
    return {"n_total":len(x),"n_observed":n,"n_missing":len(x)-n,
            "mean":float(v.mean()) if n else None,"sd":float(v.std(ddof=1)) if n>1 else None,
            "floor_count":int((v==6).sum()),"ceiling_count":int((v==42).sum()),
            "floor_fraction":float((v==6).mean()) if n else None,
            "ceiling_fraction":float((v==42).mean()) if n else None}
