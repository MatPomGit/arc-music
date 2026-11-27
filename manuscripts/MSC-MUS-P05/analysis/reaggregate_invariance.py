"""Reaggregate archived ordered decisions without refitting or modifying input."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

REJECT = {"configural_rejected", "threshold_shape_rejected",
          "threshold_loading_rejected", "threshold_loading_intercept_rejected"}
KEEP = "all_restrictions_not_rejected"


def reaggregate(data):
    output = []
    for cell in data["scenarios"]:
        records = cell["records"]
        if len(records) != cell["requested"] or len({r["replicate"] for r in records}) != len(records):
            raise ValueError("invalid requested or duplicate replication IDs")
        if any(r["status"] not in {"proper", "failure"} for r in records):
            raise ValueError("unknown replication status")
        counts = Counter(r["ordered_gate"] for r in records if r["status"] == "proper")
        if set(counts) - (REJECT | {KEEP}):
            raise ValueError("unknown ordered gate")
        proper = sum(counts.values())
        if proper != cell["proper"]:
            raise ValueError("proper count mismatch")
        rejected = sum(counts[k] for k in REJECT)
        n = len(records)
        if not n:
            raise ValueError("empty cell")
        output.append({"sizes": cell["sizes"], "scenario": cell["scenario"],
                       "requested": n, "proper": proper, "failed": n-proper,
                       "rejected": rejected, "not_rejected": counts[KEEP],
                       "old_rate": cell["any_gate_rejection_unconditional"],
                       "corrected_rate": rejected/n,
                       "corrected_conditional_rate": rejected/proper if proper else None,
                       "status_counts": dict(sorted(counts.items()))})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    with ZipFile(args.archive) as z:
        raw = z.read("p05-invariance-power.json")
    data = json.loads(raw)
    print(json.dumps({"archive_sha256": hashlib.sha256(args.archive.read_bytes()).hexdigest(),
                      "json_sha256": hashlib.sha256(raw).hexdigest(),
                      "seed": data["seed"], "offset": data["offset"],
                      "scenarios": reaggregate(data)}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
