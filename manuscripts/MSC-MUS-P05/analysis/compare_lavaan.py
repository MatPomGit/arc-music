"""Paired ordinal CFA comparison on identical synthetic complete datasets."""
import argparse
import platform
import scipy
import csv
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np

from recovery import simulate
from robust_cfa import robust_fit
from reference_inputs import encode, digest, write_input, write_manifest, replay


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


def compare(n, factors, items, loading, rho, skew, seed, x=None, *, archive_dir=None, index=0):
    if x is None:
        x = simulate(n, factors, items, loading, rho, skew, 0, np.random.default_rng(seed))
    domains = np.repeat(np.arange(factors), items)
    result = dict(n=n, factors=factors, items_per_factor=items, loading=loading,
                  rho=rho, skew=skew, seed=seed)
    estimates = ses = thresholds = None
    with tempfile.TemporaryDirectory() as directory:
        csv_in = Path(directory) / "synthetic.csv"
        csv_out = Path(directory) / "reference.csv"
        data = encode(x,factors,items)
        csv_in.write_bytes(data)
        result["input_sha256"] = digest(data)
        if archive_dir is not None:
            _, archived_digest = write_input(archive_dir,x,factors,items,index)
            if archived_digest != result["input_sha256"]:
                raise ValueError("Archived input mismatch")
        reference = Path(__file__).with_name("lavaan_reference.R")
        try:
            completed = subprocess.run(
                ["Rscript", str(reference), str(csv_in), str(factors), str(items), str(csv_out)],
                capture_output=True, text=True, check=False, timeout=300,
            )
            result["reference_warnings"] = completed.stderr.strip()
            if completed.returncode:
                raise RuntimeError(f"Rscript exited {completed.returncode}")
            meta, estimates, ses, thresholds = read_reference(csv_out, factors, items)
            result["reference"] = meta
            result["reference_status"] = reference_status(meta)
        except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, RuntimeError) as error:
            result["reference_error"] = str(error)
            result["reference_status"] = "ERROR"
    try:
        local = robust_fit(x, domains)
        result["python"] = dict(diagnostics=local.fit.diagnostics, residual_test_p=local.p_value)
        result["python_status"] = "PROPER"
        if result.get("reference_status") == "PROPER":
            delta = local.parameters - estimates
            result["agreement"] = dict(
                max_abs_loading=float(np.max(abs(delta[:x.shape[1]]))),
                max_abs_factor_correlation=float(np.max(abs(delta[x.shape[1]:]))),
                max_abs_threshold=float(np.max(abs(local.fit.thresholds.ravel()-thresholds))),
                max_abs_sandwich_se=(float(np.max(abs(np.sqrt(np.diag(local.covariance))-ses)))
                                     if np.isfinite(ses).all() else None),
            )
    except (ArithmeticError, ValueError, np.linalg.LinAlgError) as error:
        result["python_error"] = str(error)
        result["python_status"] = "IMPROPER" if str(error) == "improper DWLS fit" else "ERROR"
    result["classification"] = classify(result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Also compare the full 35-item model")
    parser.add_argument("--archive-dir", type=Path, help="Archive exact synthetic CSV inputs")
    parser.add_argument("--replay-dir", type=Path, help="Replay an exact archived synthetic input bundle")
    args = parser.parse_args()
    if args.archive_dir and args.archive_dir.exists() and any(args.archive_dir.iterdir()):
        parser.error("Archive directory must be empty")
    if args.replay_dir and args.full:
        parser.error("--full is not used with --replay-dir")
    if args.replay_dir:
        output=[]
        for i,(meta,x) in enumerate(replay(args.replay_dir)):
            row=compare(*(meta[k] for k in ("n","factors","items_per_factor","loading","rho","skew","seed")),x,
                        archive_dir=args.archive_dir,index=i)
            if row["input_sha256"]!=meta["input_sha256"]:raise ValueError("Replay input mismatch")
            if "draw" in meta:row["draw"]=meta["draw"]
            output.append(row)
    else:
        scenarios = [(800, 2, 4, .65, .35, False, 67)]
        if args.full:
            scenarios.extend([(500, 7, 5, .65, .35, False, 68),
                              (500, 7, 5, .40, .80, True, 69)])
        output = [compare(*scenario,archive_dir=args.archive_dir,index=i) for i,scenario in enumerate(scenarios)]
        if args.full:
            # First weak draw under the historical generator and sequence, not a byte-identical
            # historical dataset unless its archived digest is independently established.
            historic_seed = 20261127
            rng = np.random.default_rng(historic_seed)
            for skew, missing in [(False, 0.), (True, .02)]:
                for _ in range(8):
                    simulate(500, 7, 5, .65, .35, skew, missing, rng)
            weak = simulate(500, 7, 5, .40, .80, True, 0., rng)
            historic = compare(500, 7, 5, .40, .80, True, historic_seed, weak,
                               archive_dir=args.archive_dir,index=len(output))
            historic["draw"] = "regenerated first weak-model draw from cfa_calibration.py --reps 8"
            output.append(historic)
    if args.archive_dir:
        write_manifest(args.archive_dir,output)
    status = screen(output)
    payload = {"schema_version": 3, "versions": {"python": platform.python_version(),
               "numpy": np.__version__, "scipy": scipy.__version__},
               "input_mode":"archived_replay" if args.replay_dir else "generated",
               "tolerances": TOLERANCES, "screen": status, "scenarios": output}
    print(json.dumps(payload, indent=2, allow_nan=False))
    if not status["core_agreement"] or not status["all_cases_executed"]:
        parser.exit(1, "Reference core agreement or execution check failed.\n")
