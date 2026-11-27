"""Re-run canonical estimators for rounded candidate N, with historical defaults intact."""
import argparse
import itertools
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
from scipy.stats import binom, nct, t

ROOT = Path(__file__).resolve().parent

def analytic(n, d, df=None):
    df = n - 2 if df is None else df
    q = t.ppf(.975, df)
    nc = d * np.sqrt(n / 4)
    return float(nct.sf(q, df, nc) + nct.cdf(-q, df, nc))

def p01(reps):
    rng = np.random.default_rng(20261127)
    rows = []
    for d in (0., .30):
        n = rng.binomial(105, .85, (reps, 4))
        if (n < 2).any():
            raise ValueError("Degenerate retained cell")
        w = np.array([.5, -.5, -.5, .5])
        means = np.array([d, 0, 0, d])
        estimate = ((means + rng.normal(size=n.shape) / np.sqrt(n)) * w).sum(axis=1)
        v = w*w*rng.chisquare(n-1)/(n-1)/n
        se = np.sqrt(v.sum(axis=1))
        df = v.sum(axis=1)**2 / (v*v/(n-1)).sum(axis=1)
        half = t.ppf(.975, df)*se
        rejection = float((np.abs(estimate) > half).mean())
        coverage = float((np.abs(estimate-d) <= half).mean())
        rows.append(dict(effect=d, reps=reps, rejection=rejection, coverage=coverage,
                         rejection_mcse=float(np.sqrt(rejection*(1-rejection)/reps)),
                         coverage_mcse=float(np.sqrt(coverage*(1-coverage)/reps)),
                         bias=float(estimate.mean()-d), mean_n=float(n.sum(axis=1).mean())))
    return dict(n=420, expected_n=357, analytic_power=analytic(357,.30,353), cells=rows)

def study(study_id, reps):
    sys.path.insert(0, str(ROOT / "manuscripts" / ("MSC-MUS-" + study_id) / "analysis"))
    if study_id == "P01":
        return p01(reps)
    if study_id == "P03":
        import power
        import stress
        return dict(primary=[power.simulate(reps, seed=20261127, target=500, cap=cap)
                             for cap in (560, 580, 640)],
                    stress=[stress.simulate(reps, seed=20261129, target_complete=500,
                                           submission_cap=cap) for cap in (560, 600, 640)])
    if study_id == "P08":
        import simulation
        complete=list(itertools.product((500,), (0., .45), (0., .60), ("mcar",)))
        grid=list(itertools.product((500, 640, 660), (0., .45), (0., .60),
                                    ("mcar", "mar", "mnar")))
        return dict(complete=simulation.run(reps, 80000, seed=20261127, grid=complete, loss=0.),
                    missing=simulation.run(reps, 80000, seed=20261128, grid=grid, loss=.20),
                    nonadherence=simulation.run(reps, 80000, seed=20261129, grid=grid, loss=.20,
                                                nonadherence=.15),
                    analytic_power_500=analytic(500,.30),
                    retention=[dict(n=n, per_endpoint_at_least_500=float(binom.sf(499,n,.8)))
                               for n in (640,660)])
    if study_id == "P09":
        import calibration
        grid=list(itertools.product((440,600), calibration.PROFILES, calibration.MECHANISMS,
                                    calibration.EFFECTS))
        seeds=np.random.SeedSequence(20261127).spawn(len(grid))
        return dict(cells=[calibration.cell(seed,*cell,reps) for seed,cell in zip(seeds,grid)],
                    analytic=[dict(n=n,d=d,power=analytic(int(n*.8),d))
                              for n,d in ((440,.35),(600,.30))])
    raise ValueError("Unknown study")

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study", choices=("P01","P03","P08","P09"), required=True)
    p.add_argument("--reps", type=int, required=True)
    a=p.parse_args()
    if a.reps < 2:
        p.error("At least two replications")
    print(json.dumps(dict(synthetic=True, study=a.study, reps=a.reps,
                          results=study(a.study,a.reps)),indent=2,allow_nan=False))
