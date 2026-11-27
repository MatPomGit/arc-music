"""Prospective P08 pilot fidelity diagnostics, not confirmatory outcome analysis."""
import argparse
import itertools
import json

import numpy as np
import pandas as pd
from scipy.stats import beta, t
from inference import prepare, ITEMS

CELLS = list(itertools.product((0, 1), repeat=2))
TIMES = ("task_seconds", "preview_seconds")
FLAGS = ("roles_correct", "playback_success", "started_playback")


def rate(success, total):
    if not 0 <= success <= total:
        raise ValueError("Invalid binomial count")
    if not total:
        return dict(success=success, total=total, rate=None, ci=None)
    lo = 0. if success == 0 else float(beta.ppf(.025, success, total-success+1))
    hi = 1. if success == total else float(beta.ppf(.975, success+1, total-success))
    return dict(success=success, total=total, rate=success/total, ci=[lo, hi])


def equivalence(a, b, margin):
    """Welch 90% CI; inconclusive if missing, sparse, or zero sampling variance."""
    if not np.isfinite(margin) or margin <= 0:
        raise ValueError("Positive prespecified margin required")
    a,b = np.asarray(a,float),np.asarray(b,float)
    if min(len(a),len(b)) < 2 or not (np.isfinite(a).all() and np.isfinite(b).all()):
        return dict(status="inconclusive", reason="Missing or insufficient timing records")
    va,vb = a.var(ddof=1)/len(a),b.var(ddof=1)/len(b)
    if va+vb <= 0:
        return dict(status="inconclusive", reason="Degenerate sampling variance")
    df=(va+vb)**2/(va**2/(len(a)-1)+vb**2/(len(b)-1))
    delta=float(a.mean()-b.mean())
    half=float(t.ppf(.95,df)*np.sqrt(va+vb))
    ci=[delta-half,delta+half]
    return dict(status="equivalent" if ci[0]>-margin and ci[1]<margin else "not_established",
                difference=delta, ci90=ci, margin=margin, n=[len(a),len(b)])


def pilot(frame, task_margin, preview_margin):
    d=prepare(frame)
    if not {*TIMES,*FLAGS} <= set(d):
        raise ValueError("Missing pilot fidelity fields")
    for k in TIMES:
        v=pd.to_numeric(d[k],errors="raise")
        if not v.dropna().between(0,480).all():
            raise ValueError("Invalid timing "+k)
        d[k]=v
    if (d.preview_seconds>d.task_seconds).any():
        raise ValueError("Preview exposure exceeds task time")
    for k in FLAGS:
        if not d[k].dropna().map(lambda v:isinstance(v,(bool,np.bool_))).all():
            raise ValueError("Invalid fidelity flag "+k)
    if (d.playback_success.eq(True) & ~d.started_playback.eq(True).fillna(False)).any():
        raise ValueError("Successful playback without confirmed start")
    groups={f"{a}/{e}":d[(d.authority==a)&(d.manual==e)] for a,e in CELLS}
    out={}
    for name,g in groups.items():
        heard=g.heard_version.eq(True).fillna(False)
        started=g.started_playback.eq(True).fillna(False)
        out[name]=dict(randomised=len(g),
                       hearing=rate(int(heard.sum()),len(g)),
                       hearing_unknown=int(g.heard_version.isna().sum()),
                       role_comprehension=rate(int(g.roles_correct.eq(True).sum()),len(g)),
                       role_unknown=int(g.roles_correct.isna().sum()),
                       playback=rate(int((started & g.playback_success.eq(True)).sum()),int(started.sum())),
                       playback_start_unknown=int(g.started_playback.isna().sum()),
                       playback_unknown_among_started=int((started & g.playback_success.isna()).sum()),
                       timing_missing={k:int(g[k].isna().sum()) for k in TIMES},
                       items={k:rate(int((heard & g[k].notna()).sum()),int(heard.sum()))
                              for cols in ITEMS.values() for k in cols})
    comparisons={}
    for field,margin in zip(TIMES,(task_margin,preview_margin)):
        comparisons[field]={f"{a}:{b}":equivalence(groups[a][field],groups[b][field],margin)
                            for a,b in itertools.combinations(groups,2)}
    # All comparisons must establish equivalence for a joint claim; a pilot
    # generally lacks precision. Unknown values count as unconfirmed, not success.
    all_equal=all(v["status"]=="equivalent" for metric in comparisons.values() for v in metric.values())
    return dict(synthetic_or_approved_pilot_only=True,randomised=len(d),cells=out,
                timing=comparisons, joint_timing_equivalence=all_equal,
                note="Feasibility diagnostics, no exclusion or causal mediation.")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("csv")
    p.add_argument("--task-margin",type=float,required=True)
    p.add_argument("--preview-margin",type=float,required=True)
    a=p.parse_args()
    print(json.dumps(pilot(pd.read_csv(a.csv,dtype={"participant_id":str}),a.task_margin,a.preview_margin),
                     indent=2,allow_nan=False))
