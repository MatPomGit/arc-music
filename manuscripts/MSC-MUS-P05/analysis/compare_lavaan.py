"""Read historical external reference CSV and assess archived paired results.
New external reference execution is disabled; Python-only validation remains open.
"""
import csv
from pathlib import Path

import numpy as np



# Prospective development tolerances, not empirical measurement criteria.
TOLERANCES = {"max_abs_loading": .02, "max_abs_factor_correlation": .02,
              "max_abs_threshold": .02, "max_abs_sandwich_se": .01}


def reference_status(meta):
    if not meta["converged"]:
        return "NONCONVERGED"
    if (not meta["post_check"] or meta["minimum_uniqueness"] <= .01
            or meta["minimum_factor_eigenvalue"] <= .01):
        return "IMPROPER"
    return "PROPER"


def classify(row):
    reference = row.get("reference_status", "ERROR")
    local = row.get("python_status", "ERROR")
    if "ERROR" in (reference, local):
        return "EXECUTION_ERROR"
    if reference == local == "PROPER":
        values = row.get("agreement", {})
        ok = all(values.get(key) is not None and np.isfinite(values[key])
                 and values[key] <= tolerance for key, tolerance in TOLERANCES.items())
        return "PAIRED_AGREEMENT" if ok else "PARAMETER_DISAGREEMENT"
    if reference == local:
        return "BOTH_" + reference
    return "ADMISSIBILITY_DISAGREEMENT"


def screen(output):
    """Core cases must agree; stress nonpasses explicitly block model readiness."""
    core = [row for row in output if row["loading"] >= .60 and row["rho"] <= .50]
    return {"core_agreement": bool(core) and all(row["classification"] == "PAIRED_AGREEMENT" for row in core),
            "all_cases_executed": all(row["classification"] != "EXECUTION_ERROR" for row in output),
            "full_agreement": all(row["classification"] == "PAIRED_AGREEMENT" for row in output),
            "model_readiness_authorized": False}


def read_reference(path, factors, items):
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    meta = {
        row["lhs"]: float(row["value"]) if row["value"] != "NA" else None
        for row in rows if row["kind"] == "meta"
    }
    estimates = {(row["kind"], row["lhs"], row["rhs"]): row for row in rows}
    pair = [("~~", f"factor{j + 1}", f"factor{i + 1}")
            for i, j in zip(*np.tril_indices(factors, -1))]
    loadings = [("=~", f"factor{i // items + 1}", f"item{i + 1}")
                for i in range(factors * items)]
    thresholds = [("|", f"item{i + 1}", f"t{j + 1}")
                  for i in range(factors * items) for j in range(4)]
    meta["lavaan"] = rows[0]["rhs"]
    return (
        meta,
        np.array([float(estimates[key]["value"]) for key in loadings + pair]),
        np.array([float(estimates[key]["se"].replace("NA", "nan")) for key in loadings + pair]),
        np.array([float(estimates[key]["value"]) for key in thresholds]),
    )


def compare(*args, **kwargs):
    raise RuntimeError("Independent Python ordinal reference not established; use historical archived results only")


if __name__ == "__main__":
    raise SystemExit("BLOCKED: independent Python ordinal reference not established")
