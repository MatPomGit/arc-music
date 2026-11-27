"""Prospective same-episode agreement; no empirical scoring authorization."""
import numpy as np
from cohort_contract import audit_cohorts, CODE, FIELDS, STAGES
from validity import domain_score


def icc_a1(pairs):
    """Two-way absolute agreement, single measurement; retain negative ICCs."""
    x = np.asarray(pairs, float)
    if x.ndim != 2 or x.shape[1] != 2 or len(x) < 2 or not np.isfinite(x).all():
        raise ValueError("finite paired observations required")
    n, k = x.shape
    grand = x.mean()
    row = x.mean(axis=1)
    col = x.mean(axis=0)
    ms_row = k * np.sum((row - grand)**2) / (n - 1)
    ms_col = n * np.sum((col - grand)**2) / (k - 1)
    ms_err = np.sum((x - row[:, None] - col + grand)**2) / ((n - 1)*(k - 1))
    den = ms_row + (k - 1)*ms_err + k*(ms_col - ms_err)/n
    if den <= 0 or not np.isfinite(den):
        raise ValueError("undefined agreement")
    return float((ms_row - ms_err)/den)


def _key(row):
    return (row["participant_code"], row["stage"], row["episode_code"])


def _eligible(rows):
    """Separate eligibility from integrity. Never resolve ambiguous duplicates."""
    baselines = []
    retests = []
    seen = set()
    for i, row in enumerate(rows, 1):
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError(f"row {i}: unexpected metadata fields")
        person, stage, episode = _key(row)
        if stage not in STAGES or any(not isinstance(v, str) or not CODE.fullmatch(v)
                                      for v in (person, episode)):
            raise ValueError(f"row {i}: invalid metadata")
        slot = (person, stage)
        if slot in seen:
            raise ValueError(f"row {i}: duplicate participant-stage")
        seen.add(slot)
        (retests if stage == "retest" else baselines).append(row)
    counts = audit_cohorts(baselines)
    baseline = {r["participant_code"]: r for r in baselines if r["stage"] == "cfa"}
    excluded = dict.fromkeys(("no_cfa_parent", "episode_mismatch", "invalid_lag", "outside_window"), 0)
    eligible = []
    for r in retests:
        parent = baseline.get(r["participant_code"])
        lag = r["lag_days"]
        if parent is None:
            excluded["no_cfa_parent"] += 1
        elif r["episode_code"] != parent["episode_code"]:
            excluded["episode_mismatch"] += 1
        elif type(lag) is not int:
            excluded["invalid_lag"] += 1
        elif not 7 <= lag <= 14:
            excluded["outside_window"] += 1
        else:
            eligible.append(r)
    audit_cohorts(baselines + eligible)
    return counts, baseline, eligible, excluded


def retest_domain(rows, item_records, *, authorized=False, reps=2000, seed=20261128, min_pairs=30):
    """Keyed item records: iterable of (participant, stage, episode) key and item vector pairs.

    Reject duplicate or missing keys rather than silently overwrite. Only eligible
    linked pairs are scored, in sorted participant order. Input identity and item
    column order must already be verified by the approved export procedure.
    Results are aggregate development diagnostics, not authorization.
    """
    if authorized is not True:
        raise ValueError("frozen domain scoring not authorized")
    if type(reps) is not int or reps < 20 or type(min_pairs) is not int or min_pairs < 2:
        raise ValueError("invalid bootstrap settings")
    rows = list(rows)
    counts, baseline, eligible, excluded = _eligible(rows)
    expected = {_key(r) for r in rows}
    values = {}
    for key, items in item_records:
        if not isinstance(key, tuple) or len(key) != 3 or any(not isinstance(v, str) for v in key):
            raise ValueError("invalid item record key")
        if key in values:
            raise ValueError("duplicate item record key")
        values[key] = items
    if set(values) != expected:
        raise ValueError("metadata and item keys differ")
    eligible.sort(key=lambda r: r["participant_code"])
    pairs = []
    if eligible:
        keys = [(_key(baseline[r["participant_code"]]), _key(r)) for r in eligible]
        scores = domain_score([values[key] for pair in keys for key in pair], authorized=True)
        pairs = scores.reshape(-1, 2)
    pairs = np.asarray(pairs, float).reshape(-1, 2)
    pairs = pairs[np.isfinite(pairs).all(axis=1)]
    result = {"cfa_records": counts["cfa"], "retest_records": len(eligible)+sum(excluded.values()),
              "excluded_retests": excluded, "linked_retests": len(eligible),
              "complete_pairs": len(pairs), "incomplete_pairs": len(eligible)-len(pairs)}
    if len(pairs) < min_pairs:
        return dict(result, status="unavailable", reason="insufficient complete pairs")
    delta = pairs[:, 1] - pairs[:, 0]
    result.update(mean_difference=float(delta.mean()), sd_difference=float(delta.std(ddof=1)))
    try:
        result["icc"] = icc_a1(pairs)
    except ValueError:
        return dict(result, status="unavailable", reason="undefined agreement")
    rng = np.random.default_rng(seed)
    draws = []
    changes = []
    for _ in range(reps):
        sample = pairs[rng.integers(len(pairs), size=len(pairs))]
        changes.append(float(np.mean(sample[:, 1]-sample[:, 0])))
        try:
            draws.append(icc_a1(sample))
        except ValueError:
            pass
    result.update(bootstrap_requested=reps, bootstrap_failed=reps-len(draws),
                  difference_interval=np.quantile(changes, [.025, .975]).tolist())
    if len(draws) < .95*reps:
        return dict(result, status="interval_unavailable", reason="bootstrap failures")
    return dict(result, status="estimated", icc_interval=np.quantile(draws, [.025, .975]).tolist())
