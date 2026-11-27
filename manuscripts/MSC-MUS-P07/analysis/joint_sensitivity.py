"""Joint exposure/outcome pattern scenarios, not identified MNAR correction."""
import itertools
import numpy as np
from scipy.special import expit, logit
from inference import PRED
from sensitivity import probability, weighted_slope

def assess_joint(d, draws=100, seed=2709):
    if draws < 1:
        raise ValueError("Positive draws required")
    a=d.loc[d.baseline_valid].copy()
    g=a.participant_id.to_numpy()
    cov=a[PRED[1:]].to_numpy(float)
    e=a.exposure_valid.to_numpy(bool)
    o=a.outcome60_valid.to_numpy(bool)
    c=np.where(e,a.creation_first_hour,np.nan).astype(float)
    y=np.where(o,a.valence60,np.nan)
    complete=e&o
    if not complete.any():
        raise ValueError("No complete windows for working outcome model")
    # Offsets are estimable only for persons with a complete known window.
    ids,ix=np.unique(g[complete],return_inverse=True)
    included=np.isin(g,ids)
    x=np.column_stack([c,cov])
    b=weighted_slope(g[complete],x[complete],y[complete],np.ones(complete.sum()))
    offsets=np.bincount(ix,weights=y[complete]-x[complete]@b)/np.bincount(ix)
    lookup=dict(zip(ids,offsets))
    out={"valid_baselines":len(a),"included_windows":int(included.sum()),
         "excluded_windows":int((~included).sum()),"included_participants":len(ids),
         "excluded_participants":int(len(np.unique(g))-len(ids)),
         "both_missing_included":int((~e&~o&included).sum()),"draws":draws,"seed":seed,
         "complete_case_beta":float(b[0]),
         "interpretation":"Fixed working models, conditional-mean outcomes and exposure scenarios; quantiles are not confidence intervals. Restricts to valid baselines with at least one complete known window per participant. Not a causal or identified full-window estimate."}
    g,cov,e,o,c,y=g[included],cov[included],e[included],o[included],c[included],y[included]
    offset=np.array([lookup[i] for i in g])
    # Observed outcome information is used only when available; the mask
    # distinguishes a missing outcome from zero change from baseline.
    design=np.column_stack([cov,o.astype(float),np.where(o,y-cov[:,0],0.)])
    if (~e).any():
        p=np.clip(probability(design[e],c[e])(design),.001,.999)
        logits=logit(p)
    else:
        logits=np.zeros(len(g))
    uniforms=np.random.default_rng(seed).random((draws,len(g)))
    scenarios={}
    for shift,diff in itertools.product((-1.,0.,1.),repeat=2):
        values=[]
        q=expit(logits+shift)
        for u in uniforms:
            filled_c=np.where(e,c,(u<q).astype(float))
            design_x=np.column_stack([filled_c,cov])
            # Missing creation outcomes shift relative to missing
            # noncreation outcomes. Keep known outcomes unchanged.
            pred=np.clip(offset+design_x@b+diff*filled_c,0,10)
            filled_y=np.where(o,y,pred)
            try:
                values.append(float(weighted_slope(g,design_x,filled_y,np.ones(len(g)))[0]))
            except (ValueError,np.linalg.LinAlgError):
                continue
        scenarios[f"{shift:+.0f}/{diff:+.0f}"]={
            "exposure_log_odds_shift":shift,"missing_creation_outcome_shift":diff,
            "valid":len(values),"failed":draws-len(values),
            "median":float(np.median(values)) if values else None,
            "scenario_quantiles":np.quantile(values,[.025,.975]).tolist() if values else None}
    out["scenarios"]=scenarios
    return out
