"""Prospective same-episode agreement; no empirical scoring authorization."""
import numpy as np
from cohort_contract import audit_cohorts
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


def retest_domain(rows, items, *, authorized=False, reps=2000, seed=20261128, min_pairs=30):
    """Rows and frozen-domain item matrix share the same order. Return aggregates only.

    Invalid metadata blocks analysis. Minimum pair count and percentile
    bootstrap are provisional development choices, not calibrated criteria.
    """
    if authorized is not True:
        raise ValueError("frozen domain scoring not authorized")
    if type(reps) is not int or reps < 20 or type(min_pairs) is not int or min_pairs < 2:
        raise ValueError("invalid bootstrap settings")
    rows = list(rows)
    counts = audit_cohorts(rows)
    scores = domain_score(items, authorized=True)
    if len(scores) != len(rows):
        raise ValueError("metadata and item row counts differ")
    baseline = {r["participant_code"]: i for i, r in enumerate(rows) if r["stage"] == "cfa"}
    linked = [(baseline[r["participant_code"]], i) for i, r in enumerate(rows) if r["stage"] == "retest"]
    pairs = np.asarray([(scores[i], scores[j]) for i, j in linked], float).reshape(-1, 2)
    pairs = pairs[np.isfinite(pairs).all(axis=1)]
    result = {"cfa_records": counts["cfa"], "linked_retests": len(linked),
              "complete_pairs": len(pairs), "incomplete_pairs": len(linked)-len(pairs)}
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
