"""Preliminary checks only; not a validated scale or latent-model power analysis."""
from math import atanh, ceil, isfinite
from statistics import NormalDist

def correlation_sample_size(r: float, power: float = .80, alpha: float = .05) -> int:
    """Fisher-z approximation, independent pairs, two-sided test of zero."""
    if not 0 < abs(r) < 1 or not 0 < power < 1 or not 0 < alpha < 1:
        raise ValueError("invalid design parameters")
    n = NormalDist()
    return ceil(3 + ((n.inv_cdf(1-alpha/2) + n.inv_cdf(power))/atanh(abs(r)))**2)

def candidate_domain_mean(values, *, validated: bool = False):
    """Illustrative scoring rule, disabled until separately authorised/validated."""
    if not validated:
        raise ValueError("candidate scoring is not authorised")
    values = list(values)
    if len(values) < 3:
        raise ValueError("at least three retained items required")
    observed = [v for v in values if v is not None]
    if any(isinstance(v, bool) or not isinstance(v, (int,float))
           or not isfinite(v) or v not in (0,1,2,3,4) for v in observed):
        raise ValueError("invalid item response")
    if len(observed) < ceil(.8 * len(values)):
        return None
    return sum(observed) / len(observed)
