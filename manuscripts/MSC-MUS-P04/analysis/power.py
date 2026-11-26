"""Idealised interaction sensitivity; no human data or fitted effects."""
from math import sqrt, ceil, isfinite
from statistics import NormalDist
import json

NORMAL = NormalDist()

def power(n, delta, alpha=0.05):
    """Balanced arms, standardised moderator, residual SD=1."""
    if not isinstance(n, int) or n < 4 or not isfinite(delta) or not 0 < alpha < 1:
        raise ValueError("Invalid sample size, effect or alpha")
    z = NORMAL.inv_cdf(1-alpha/2)
    shift = abs(delta)*sqrt(n)/2
    return NORMAL.cdf(-z-shift) + NORMAL.cdf(shift-z)

def required_n(delta, target=0.8, alpha=0.05):
    if not isfinite(delta) or delta == 0 or not alpha < target < 1 or not 0 < alpha < 1:
        raise ValueError("Invalid design parameters")
    lo, hi = 4, 4
    while power(hi, delta, alpha) < target:
        hi *= 2
    while lo < hi:
        mid = (lo+hi)//2
        if power(mid, delta, alpha) >= target:
            hi = mid
        else:
            lo = mid+1
    return lo

def report():
    return {"status": "DESIGN_ONLY", "alpha": .05,
            "assumptions": "balanced independent assignment, unit-variance moderator and residual, normal approximation",
            "scenarios": [{"observed_n": n, "interaction_residual_sd": d,
                           "power": power(n,d)}
                          for n in (320,480,640,800) for d in (.15,.20,.26,.30)],
            "required_observed_n_at_80_percent": {str(d): required_n(d) for d in (.15,.20,.26,.30)},
            "randomised_cap": 1000,
            "expected_observed_at_20_percent_missing": 800}

if __name__ == "__main__":
    print(json.dumps(report(), indent=2))
