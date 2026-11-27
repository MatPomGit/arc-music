"""Candidate global familywise-error gate for five ordinal diagnostics.

The family contains two group-fit and three cumulative restriction tests.
Holm controls FWER under arbitrary dependence if individual null p-values
are valid. This is a development candidate, not validated WLSMV.
"""
import math

NAMES = ("configural_1", "configural_2", "threshold_shape",
         "threshold_loading", "threshold_loading_intercept")


def global_decision(configural, tests, alpha=.05):
    if not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("invalid alpha")
    if len(configural) != 2 or set(tests) != set(NAMES[2:]):
        raise ValueError("all five test slots required")
    p = dict(zip(NAMES, [*configural, *(tests[k]["p_value"] for k in NAMES[2:])]))
    if any(not math.isfinite(v) or not 0 <= v <= 1 for v in p.values()):
        raise ValueError("invalid p-value")
    adjusted = {}
    prev = 0.
    for i, key in enumerate(sorted(NAMES, key=lambda k:p[k])):
        prev = max(prev, min(1., (len(NAMES)-i)*p[key]))
        adjusted[key] = prev
    rejected = [k for k in NAMES if adjusted[k] <= alpha]
    if any(k in rejected for k in NAMES[:2]):
        gate = "configural_rejected"
    else:
        gate = next((k+"_rejected" for k in NAMES[2:] if k in rejected),
                    "all_restrictions_not_rejected")
    return {"rule":"holm_five_v1", "alpha":alpha, "adjusted_p":adjusted,
            "rejected_tests":rejected, "any_rejected":bool(rejected),
            "ordered_gate":gate, "latent_mean_comparison_authorized":False,
            "confirmatory_authorized":False}
