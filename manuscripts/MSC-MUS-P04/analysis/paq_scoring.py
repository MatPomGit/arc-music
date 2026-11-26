"""Numeric scoring of the full PAQ-PL; no questionnaire text or respondent records.

Source: Larionow, Preece & Mudło-Głagolska (2022), scoring instructions,
https://repozytorium.ukw.edu.pl/handle/item/8068, page 4.
Use only with the approved Polish 24-item instrument, original item order.
"""
import numpy as np

FACETS = {
    "nddf": (1, 7, 13, 19),
    "ndif": (2, 8, 14, 20),
    "pddf": (4, 10, 16, 22),
    "pdif": (5, 11, 17, 23),
    "geot": (3, 6, 9, 12, 15, 18, 21, 24),
}
COMPOSITES = {
    "gdif": ("ndif", "pdif"),
    "gddf": ("nddf", "pddf"),
    "ndaf": ("ndif", "nddf"),
    "pdaf": ("pdif", "pddf"),
    "gdaf": ("ndif", "pdif", "nddf", "pddf"),
    "total": ("nddf", "ndif", "pddf", "pdif", "geot"),
}

def validate_items(items):
    """N x 24 numeric array; NaN means unavailable, never zero or prorated."""
    raw=np.asarray(items)
    if raw.ndim!=2 or raw.shape[1]!=24:
        raise ValueError("Expected N x 24 in original PAQ order")
    if raw.dtype.kind not in "iuf":
        raise ValueError("Numeric item responses required")
    x=raw.astype(float)
    if np.isinf(x).any():
        raise ValueError("Infinite response")
    valid=x[np.isfinite(x)]
    if np.any((valid<1)|(valid>7)|(valid!=np.floor(valid))):
        raise ValueError("Responses must be integers 1 to 7 or NaN")
    return x

def score(items):
    """Return all five facets, six composites and explicit baseline eligibility."""
    x=validate_items(items)
    out={name:x[:,np.asarray(indices)-1].sum(axis=1)
         for name,indices in FACETS.items()}
    for name,parts in COMPOSITES.items():
        out[name]=np.sum(np.column_stack([out[key] for key in parts]),axis=1)
    out["h1_h3_baseline_eligible"]=np.isfinite(out["nddf"])
    out["h2_common_baseline_eligible"]=np.isfinite(out["nddf"])&np.isfinite(out["ndif"])
    return out

def describe_scores(values, minimum, maximum):
    """Observed score distributions; denominators explicit, no clinical thresholds."""
    x=np.asarray(values,float)
    if x.ndim!=1 or np.isinf(x).any() or minimum>=maximum:
        raise ValueError("Invalid scores or bounds")
    v=x[np.isfinite(x)]
    if np.any((v<minimum)|(v>maximum)|(v!=np.floor(v))):
        raise ValueError("Score outside instrument bounds")
    n=len(v)
    return {"n_total":len(x),"n_observed":n,"n_missing":len(x)-n,
            "mean":float(v.mean()) if n else None,
            "sd":float(v.std(ddof=1)) if n>1 else None,
            "floor_count":int((v==minimum).sum()),"ceiling_count":int((v==maximum).sum()),
            "floor_fraction":float((v==minimum).mean()) if n else None,
            "ceiling_fraction":float((v==maximum).mean()) if n else None}
