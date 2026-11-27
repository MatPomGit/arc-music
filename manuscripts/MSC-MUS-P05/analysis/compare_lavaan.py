"""Paired ordinal CFA comparison on identical synthetic complete datasets."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np

from recovery import simulate
from robust_cfa import robust_fit


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


def compare(n, factors, items, loading, rho, skew, seed, x=None):
    if x is None:
        x = simulate(n, factors, items, loading, rho, skew, 0, np.random.default_rng(seed))
    domains = np.repeat(np.arange(factors), items)
    result = dict(n=n, factors=factors, items_per_factor=items, loading=loading,
                  rho=rho, skew=skew, seed=seed)
    with tempfile.TemporaryDirectory() as directory:
        csv_in = Path(directory) / "synthetic.csv"
        csv_out = Path(directory) / "reference.csv"
        header = ",".join(f"item{i + 1}" for i in range(x.shape[1]))
        np.savetxt(csv_in, x, fmt="%d", delimiter=",", header=header, comments="")
        reference = Path(__file__).with_name("lavaan_reference.R")
        completed = subprocess.run(
            ["Rscript", str(reference), str(csv_in), str(factors), str(items), str(csv_out)],
            capture_output=True, text=True, check=False, timeout=300,
        )
        result["reference_warnings"] = completed.stderr.strip()
        if completed.returncode:
            result["reference_error"] = f"Rscript exited {completed.returncode}"
            return result
        meta, estimates, ses, thresholds = read_reference(csv_out, factors, items)
    result["reference"] = meta
    try:
        local = robust_fit(x, domains)
    except (ArithmeticError, ValueError, np.linalg.LinAlgError) as error:
        result["python_error"] = str(error)
        return result
    result["python"] = dict(diagnostics=local.fit.diagnostics, residual_test_p=local.p_value)
    if meta["post_check"]:
        delta = local.parameters - estimates
        result["agreement"] = dict(
            max_abs_loading=float(np.max(abs(delta[:x.shape[1]]))),
            max_abs_factor_correlation=float(np.max(abs(delta[x.shape[1]:]))),
            max_abs_threshold=float(np.max(abs(local.fit.thresholds.ravel()-thresholds))),
            max_abs_sandwich_se=(float(np.max(abs(np.sqrt(np.diag(local.covariance))-ses)))
                                 if np.isfinite(ses).all() else None),
        )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Also compare the full 35-item model")
    args = parser.parse_args()
    scenarios = [(800, 2, 4, .65, .35, False, 67)]
    if args.full:
        scenarios.extend([(500, 7, 5, .65, .35, False, 68),
                          (500, 7, 5, .40, .80, True, 69)])
    output = [compare(*scenario) for scenario in scenarios]
    if args.full:
        # First weak-model draw from the historic 0/8 conditional-weight run.
        historic_seed = 20261127
        rng = np.random.default_rng(historic_seed)
        for skew, missing in [(False, 0.), (True, .02)]:
            for _ in range(8):
                simulate(500, 7, 5, .65, .35, skew, missing, rng)
        weak = simulate(500, 7, 5, .40, .80, True, 0., rng)
        historic = compare(500, 7, 5, .40, .80, True, historic_seed, weak)
        historic["draw"] = "first weak-model draw in cfa_calibration.py --reps 8"
        output.append(historic)
    print(json.dumps(output, indent=2, allow_nan=False))
    if "agreement" not in output[0]:
        parser.exit(1, "Reference smoke comparison did not produce paired estimates.\n")
