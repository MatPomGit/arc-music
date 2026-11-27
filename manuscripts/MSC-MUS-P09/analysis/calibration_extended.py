"""Repeated-sample screening of P09 sensitivity estimators and raw-record gates."""
import argparse
import itertools
import json

import numpy as np
import pandas as pd
from scipy.special import expit
from calibration import EFFECTS, generate, proportion, effect_values, PROFILES
from inference import MODELS, ITEMS, prepare, design, fit_arrays, holm
from missingness import sensitivity_endpoint

METHODS = ("ipw", "shift_0/0")
# Two H1 effects under each mechanism; secondary endpoints under MAR and MNAR.
BOOT_GRID = [(h, m, e) for h, m, e in itertools.product(
    MODELS, ("complete", "MCAR", "MAR", "MNAR"), EFFECTS)
    if h == "H1" or (m in ("MAR", "MNAR") and e == "alternative")]


def summary(rows, truth, attempts):
    points = [x["contrast"] for x in rows]
    valid = [x["ci"] for x in rows if x["ci"] is not None]
    errors = np.asarray(points) - truth
    return dict(truth=truth, attempted=attempts, point_fits=len(points),
                point_failures=attempts-len(points), intervals=len(valid),
                interval_failures=attempts-len(valid),
                bias=float(errors.mean()) if len(errors) else None,
                bias_mcse=float(errors.std(ddof=1)/np.sqrt(len(errors))) if len(errors)>1 else None,
                rmse=float(np.sqrt(np.mean(errors**2))) if len(errors) else None,
                conditional_coverage=proportion([a <= truth <= b for a,b in valid]),
                operational_coverage=proportion([a <= truth <= b for a,b in valid]
                                                + [False]*(attempts-len(valid))),
                zero_exclusion=proportion([a > 0 or b < 0 for a,b in valid]),
                mean_width=float(np.mean([b-a for a,b in valid])) if valid else None)


def bootstrap_cell(seed, hypothesis, mechanism, effect, n, reps, draws, *, profile="standard", allocation="balanced"):
    rng = np.random.default_rng(seed)
    truth = dict(zip(MODELS, effect_values(effect)))[hypothesis]
    outcome, _ = MODELS[hypothesis]
    rows = {m: [] for m in METHODS}
    envelopes = []
    warning = []
    for _ in range(reps):
        d = generate(rng, n, profile, mechanism, effect, allocation=allocation)
        d["status"] = "defined"
        report = sensitivity_endpoint(d, outcome, "status", draws,
                                      int(rng.integers(0, 2**32)))
        if "response_diagnostics" in report:
            warning.append(any(x["positivity_warning"] for x in report["response_diagnostics"]))
        estimates = report.get("estimates", {})
        for key in METHODS:
            if key in estimates:
                rows[key].append(estimates[key])
        shifts = [x["contrast"] for key,x in estimates.items() if key.startswith("shift_")]
        if len(shifts) == 25:
            envelopes.append(min(shifts) <= truth <= max(shifts))
    return dict(hypothesis=hypothesis, missingness=mechanism, effect=effect, n=n,
                profile=profile, allocation=allocation,
                methods={m: summary(v, truth, reps) for m,v in rows.items()},
                positivity_warning=proportion(warning),
                shift_point_envelope_contains_truth=proportion(envelopes),
                envelope_note="Descriptive range of scenario point estimates, not a confidence interval",
                coverage_note="MNAR coverage of full-data truth is stress performance, not nominal coverage of an identified estimand")


def raw_record(rng, n, effect, mode):
    """Actual integer item data with independently varied reasons for invalid assessment."""
    if mode not in ("independent", "selective"):
        raise ValueError("Unknown observation profile")
    z = np.repeat([0,1], n//2)
    rng.shuffle(z)
    base_p = rng.beta(8, 8, n)
    base = rng.binomial(10, base_p[:,None], size=(n,3))
    distance0 = rng.binomial(10, .5, n)
    truth = EFFECTS[effect]
    p = .5 + .55*(base.mean(axis=1)/10-.5)
    frame = pd.DataFrame(dict(participant_id=[f"s{i}" for i in range(n)], music=z,
                             training=rng.binomial(1,.4,n), importance0=rng.integers(0,11,n),
                             prior_use_days=rng.integers(0,31,n), distance0=distance0,
                             randomised_at="2026-01-01T10:00:00+00:00"))
    for col, values in zip(ITEMS[0], base.T):
        frame[col] = values
    distance1 = rng.binomial(10, .5 + .5*(distance0/10-.5)+z*truth[2]/10)
    frame["distance1"] = distance1.astype(float)
    expected = {}
    for j in (1,2):
        mu = p + z*truth[0 if j==2 else 1]/10
        latent = rng.beta(mu*20, (1-mu)*20)
        scores = rng.binomial(10, latent[:,None], size=(n,3)).astype(float)
        difficulty = np.zeros(n) if mode=="independent" else .45*z-.30*(scores.mean(axis=1)-5)
        late = rng.random(n) < expit(-3.0+difficulty)
        wrong = rng.random(n) < expit(-3.3+difficulty)
        unknown = rng.random(n) < .02
        skipped = rng.random((n,3)) < expit(-4.2+difficulty)[:,None]
        scores[skipped] = np.nan
        event = np.full(n, True, dtype=object)
        event[wrong] = False
        event[unknown] = None
        frame[f"same_event{j}"] = event
        good, bad = (("2026-01-01T10:15:00+00:00","2026-01-01T11:00:00+00:00") if j==1 else
                     ("2026-01-08T10:00:00+00:00","2026-01-10T10:00:00+00:00"))
        frame[f"t{j}_at"] = np.where(late,bad,good)
        frame[f"target_status{j}"] = "defined"
        for col, values in zip(ITEMS[j], scores.T):
            frame[col] = values
        valid = ~(late | wrong | unknown)
        expected[f"valid{j}"] = valid
        expected[f"understanding{j}"] = valid & ~skipped.any(axis=1)
    expected["distance1"] = expected["valid1"]
    return frame, expected


def raw_cell(seed, n, effect, mode, reps):
    rng = np.random.default_rng(seed)
    truth = dict(zip(MODELS, EFFECTS[effect]))
    rows = {h: [] for h in MODELS}
    rates = {h: [] for h in MODELS}
    fwer = []
    for _ in range(reps):
        frame, expected = raw_record(rng, n, effect, mode)
        d = prepare(frame)
        for key, mask in expected.items():
            got = d[key].to_numpy(bool) if key.startswith("valid") else d[key].notna().to_numpy()
            if not np.array_equal(got, mask):
                raise AssertionError("Raw observation contract failed: "+key)
        secondary = {}
        for h,(o,b) in MODELS.items():
            selected = d[d[o].notna()]
            rates[h].append(float(len(selected)/n))
            try:
                fit = fit_arrays(design(selected,b), selected[o].to_numpy(float))
            except (ValueError,np.linalg.LinAlgError):
                fit = None
            if fit is not None:
                rows[h].append(dict(contrast=fit["beta"], ci=fit["ci"]))
            if h!="H1":
                secondary[h] = None if fit is None else fit["p"]
        adj = holm(secondary)
        fwer.append(any(adj[h] is not None and adj[h]<.05 for h in adj if truth[h]==0))
    return dict(n=n, effect=effect, mode=mode,
                hypotheses={h: dict(summary(rows[h], truth[h], reps),
                                     mean_observed=float(np.mean(rates[h]))) for h in MODELS},
                secondary_false_rejection=proportion(fwer))


def run(seed, n, reps, draws, raw_reps, smoke=False):
    if min(reps, draws, raw_reps)<2 or n<20 or n%2:
        raise ValueError("Invalid replication or sample count")
    bg = BOOT_GRID[:1] if smoke else BOOT_GRID
    rg = [("null","independent")] if smoke else list(itertools.product(EFFECTS, ("independent","selective")))
    seeds = np.random.SeedSequence(seed).spawn(len(bg)+len(rg))
    return dict(schema_version=1, synthetic=True, seed=seed, outer_reps=reps,
                bootstrap_draws=draws, raw_reps=raw_reps, n=n,
                bootstrap=[bootstrap_cell(s,*g,n,reps,draws) for s,g in zip(seeds,bg)],
                raw=[raw_cell(s,n,*g,raw_reps) for s,g in zip(seeds[len(bg):],rg)])


def stress_run(seed, reps, draws):
    """Separate screening grid; not a replacement for archived calibration."""
    if min(reps, draws) < 2:
        raise ValueError("Invalid replication count")
    grid = [(h, m, e, n, profile) for h, m, e, n, profile in itertools.product(
        ("H1", "H3"), ("MAR_nonlinear", "MAR_low_overlap"),
        ("null", "distance_only"), (434, 588), PROFILES)
        if h == "H3" or e == "null"]
    seeds = np.random.SeedSequence(seed).spawn(len(grid))
    return dict(schema_version=1, synthetic=True, seed=seed, outer_reps=reps,
                bootstrap_draws=draws, purpose="exploratory stress screening",
                cells=[bootstrap_cell(s, h, m, e, n, reps, draws,
                                      profile=p, allocation="stratified_blocks")
                       for s, (h, m, e, n, p) in zip(seeds, grid)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed",type=int,default=20261128)
    parser.add_argument("--n",type=int,default=588)
    parser.add_argument("--reps",type=int,default=30)
    parser.add_argument("--draws",type=int,default=99)
    parser.add_argument("--raw-reps",type=int,default=200)
    parser.add_argument("--smoke",action="store_true")
    parser.add_argument("--stress",action="store_true")
    a=parser.parse_args()
    result = stress_run(a.seed,a.reps,a.draws) if a.stress else run(a.seed,a.n,a.reps,a.draws,a.raw_reps,a.smoke)
    print(json.dumps(result,indent=2,allow_nan=False))
