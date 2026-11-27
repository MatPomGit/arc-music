"""Separate augmented-IPW development candidate, never confirmatory.

Within each randomized arm, estimate the marginal mean with the average
outcome-regression prediction plus inverse-response-weighted residual.
The same defined-target/overlap/centered-bootstrap gate is used as for IPW.
No empirical adoption or MNAR identification is implied.
"""
import numpy as np
from missingness import covariates, response_probability
from assignment_candidate import candidate_test
from inference import MODELS,holm

def augmented_arm(d,outcome):
    if d.empty:raise ValueError("Empty assigned arm")
    x=covariates(d)
    y=d[outcome].to_numpy(float)
    if np.isinf(y).any():raise ValueError("Infinite outcome")
    obs=np.isfinite(y)
    if not obs.any():raise ValueError("No observed outcomes in assigned arm")
    if np.any((y[obs]<0)|(y[obs]>10)):raise ValueError("Observed score outside [0,10]")
    prob=response_probability(x,obs)
    w=1/prob[obs]
    ess=float(w.sum()**2/(w@w))
    diag={"n":len(y),"observed":int(obs.sum()),"min_probability":float(prob.min()),
          "max_weight":float(w.max()),"effective_n":ess,
          "positivity_warning":bool(prob.min()<.05 or ess<.5*obs.sum())}
    if obs.all():
        return float(y.mean()),dict(diag,outcome_model="not needed for complete data")
    if obs.sum()<=x.shape[1] or np.linalg.matrix_rank(x[obs])!=x.shape[1]:
        raise ValueError("Outcome regression rank/size insufficient")
    beta=np.linalg.lstsq(x[obs],y[obs],rcond=None)[0]
    prediction=x@beta
    if not np.isfinite(prediction).all():raise ValueError("Nonfinite outcome prediction")
    # Do not clip predictions or the final estimate: that changes the estimating
    # equation and obscures misspecification. Report any extrapolation.
    mean=float(prediction.mean()+np.sum((y[obs]-prediction[obs])/prob[obs])/len(y))
    return mean,dict(diag,outcome_model="arm-specific OLS with baseline covariates",
                     prediction_outside_range=int(((prediction<0)|(prediction>10)).sum()),
                     mean_outside_range=bool(mean<0 or mean>10))

def augmented_point(d,outcome):
    a0,a1=[augmented_arm(d[d.music==a],outcome) for a in (0,1)]
    return a1[0]-a0[0],[a0[1],a1[1]]

def augmented_family(d,reps=999,seed=20261127):
    seeds=np.random.SeedSequence(seed).spawn(len(MODELS))
    rows={h:candidate_test(d,o,"target_status2" if h=="H1" else "target_status1",reps,s,
                            point_estimator=augmented_point)
          for (h,(o,_)),s in zip(MODELS.items(),seeds)}
    return {"hypotheses":rows,"candidate_secondary_holm":holm({h:rows[h].get("candidate_p") for h in ("H2","H3")}),
            "method":"AIPW linear outcome model, arm-specific response model",
            "confirmatory_available":False}
