"""Prespecified descriptive robustness checks for P03; not additional confirmatory tests."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from intake import read_records
import statsmodels.api as sm
from statsmodels.miscmodels.ordinal_model import OrderedModel
from statsmodels.tools.sm_exceptions import PerfectSeparationError, PerfectSeparationWarning, ConvergenceWarning
import warnings
from statsmodels.stats.outliers_influence import variance_inflation_factor
from models import MODELS, prepare, design, fit

KNOTS = (0., 3., 7., 10.)


def basis(x):
    x = np.asarray(x, dtype=float)
    a,b,c,d = KNOTS
    return np.column_stack([
        (np.maximum(x-k,0)**3 - np.maximum(x-c,0)**3*(d-k)/(d-c)
         + np.maximum(x-d,0)**3*(c-k)/(d-c))/100 for k in (a,b)])


def nonlinear(data):
    y,x,target = design(data,"H1")
    x = x.copy()
    x[["rcs1","rcs2"]] = basis(x[target])
    if np.linalg.matrix_rank(x) < x.shape[1]:
        raise ValueError("Rank-deficient spline design")
    result=sm.OLS(y,x).fit(cov_type="HC3",use_t=True)
    rows=[]
    for score in (0,2,4,6,8,10):
        contrast=np.zeros(x.shape[1]); contrast[x.columns.get_loc(target)]=score-5
        contrast[-2:]=(basis([score])-basis([5]))[0]
        est=result.t_test(contrast)
        point=float(np.asarray(est.effect).item()); lo,hi=est.conf_int()[0]
        if not np.isfinite([point,lo,hi]).all():
            raise ValueError("Nonfinite spline inference")
        rows.append(dict(score=score,difference=point,ci95=[float(lo),float(hi)]))
    return dict(n=len(y),knots=list(KNOTS),reference_score=5,pointwise_contrasts=rows)


def threshold_diagnostics(y, x, target):
    """Descriptive cumulative-logit slopes on the same complete records.

    Threshold fits are dependent; differences are not a formal assumption test.
    Rare splits and failed fits stay visible rather than disappearing.
    """
    categories = sorted(int(v) for v in y.unique())
    rows = []
    design = sm.add_constant(x, has_constant="add")
    for cut in categories[:-1]:
        binary = (y > cut).astype(int)
        counts = [int((binary == 0).sum()), int(binary.sum())]
        row = dict(threshold=cut, n_below_or_equal=counts[0], n_above=counts[1])
        if min(counts) <= design.shape[1]:
            row.update(status="insufficient_split", beta=None, ci95=None)
        else:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", PerfectSeparationWarning)
                    warnings.simplefilter("error", ConvergenceWarning)
                    result = sm.Logit(binary, design).fit(
                        method="newton", maxiter=100, disp=False, cov_type="HC0")
                beta = float(result.params[target])
                lo, hi = result.conf_int().loc[target]
                if not result.mle_retvals.get("converged", False) or not np.isfinite([beta, lo, hi]).all():
                    raise ValueError("Nonconvergent or nonfinite threshold fit")
                row.update(status="estimated", beta=beta, ci95=[float(lo), float(hi)])
            except (ValueError, ArithmeticError, np.linalg.LinAlgError,
                    PerfectSeparationError, PerfectSeparationWarning, ConvergenceWarning):
                row.update(status="not_estimable", beta=None, ci95=None)
        rows.append(row)
    estimated = sum(row["status"] == "estimated" for row in rows)
    return dict(status="descriptive_only" if estimated >= 2 else "insufficient_thresholds",
                thresholds=rows, estimated_thresholds=estimated,
                formal_test=False, assumption_verified=False,
                interpretation="Compare slopes for P(Y > threshold); dependent pointwise intervals are not an equality test.")


def ordinal(data,h):
    y,x,target=design(data,h)
    if not np.all(y==np.rint(y)) or y.nunique()<2:
        raise ValueError("Ordinal model requires integer ratings and at least two observed categories")
    x=x.drop(columns="const")
    # Scale background age for optimizer only; target remains in original units.
    x["age"]=x.age/10
    model=OrderedModel(y.astype(int),x,distr="logit")
    result=model.fit(method="bfgs",disp=False,maxiter=500,cov_type="HC0")
    if not result.mle_retvals.get("converged",False):
        raise ValueError("Ordinal optimization did not converge")
    beta=float(result.params[target]); lo,hi=result.conf_int().loc[target]
    odds=np.exp([beta,lo,hi])
    if not np.isfinite(odds).all():
        raise ValueError("Nonfinite ordinal odds ratio")
    return dict(n=len(y),categories=sorted(int(v) for v in y.unique()),
                common_odds_ratio=float(odds[0]),ci95=[float(odds[1]),float(odds[2])],
                assumption="proportional odds; descriptive sensitivity",
                threshold_diagnostics=threshold_diagnostics(y,x,target))


def diagnostics(data,h):
    y,x,target=design(data,h)
    result=sm.OLS(y,x).fit(); influence=result.get_influence()
    vif={k:float(variance_inflation_factor(x.to_numpy(),i))
         for i,k in enumerate(x.columns) if k!="const"}
    residual=np.asarray(result.resid); leverage=influence.hat_matrix_diag
    cooks=influence.cooks_distance[0]
    return dict(n=len(y),vif=vif,leverage_above_2p_over_n=int((leverage>2*x.shape[1]/len(y)).sum()),
                cooks_above_4_over_n=int((cooks>4/len(y)).sum()),
                residual_quantiles=[float(v) for v in np.quantile(residual,[0,.25,.5,.75,1])])


def safe(call):
    try:
        return call()
    except (ValueError,np.linalg.LinAlgError,RuntimeError) as exc:
        return {"error":str(exc)}


def run(raw):
    data,_=prepare(raw)
    return dict(intake_flow=data.attrs["intake_flow"],nonlinear_H1=safe(lambda:nonlinear(data)),
                ordinal={h:safe(lambda:ordinal(data,h)) for h in MODELS},
                recent_H1=safe(lambda:fit(data.loc[data.recency<=7],"H1")),
                diagnostics={h:safe(lambda:diagnostics(data,h)) for h in MODELS})


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("csv",type=Path)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--data-kind",choices=["synthetic","empirical"],required=True)
    a=p.parse_args(); result=run(read_records(a.csv)); result["data_kind"]=a.data_kind
    a.out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
