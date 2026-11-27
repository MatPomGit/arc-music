"""Prospective P04 stimulus manifest metadata gate; never authorises recruitment."""
import argparse
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

FIELDS = (
    "asset_id", "asset_kind", "asset_version", "source", "model",
    "model_version", "generated_at", "edited_at", "duration_seconds",
    "loudness_normalisation", "rights_basis", "public_clearance_reference", "sha256",
)
KINDS = {"instrumental_excerpt", "emotion_language_bank"}
PLACEHOLDERS = {"", "unknown", "pending", "tbd", "todo", "n/a", "none", "unverified"}


def validate_manifest(path):
    """Return structural errors and counts. A header-only register is not ready."""
    errors = []
    counts = dict.fromkeys(sorted(KINDS), 0)
    seen_ids, seen_hashes = set(), set()
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELDS:
            return ["Invalid manifest columns or order"], counts
        for line, raw in enumerate(reader, 2):
            def error(message):
                errors.append(f"row {line}: {message}")
            if None in raw or any(v is None for v in raw.values()):
                error("Unexpected number of fields")
                continue
            row = {k: v.strip() for k, v in raw.items()}
            for field in ("asset_id", "asset_version", "source", "generated_at",
                          "rights_basis", "public_clearance_reference", "sha256"):
                if row[field].casefold() in PLACEHOLDERS:
                    error(f"Missing or unresolved {field}")
            asset_id = row["asset_id"]
            if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}", asset_id):
                error("Invalid asset_id")
            if asset_id in seen_ids:
                error("Duplicate asset_id")
            seen_ids.add(asset_id)
            digest = row["sha256"]
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                error("Invalid lowercase SHA-256")
            if digest in seen_hashes:
                error("Duplicate asset hash")
            seen_hashes.add(digest)
            if bool(row["model"]) != bool(row["model_version"]):
                error("Model and model version must be supplied together")
            dates = {}
            for field in ("generated_at", "edited_at"):
                if not row[field] and field == "edited_at":
                    continue
                try:
                    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row[field]):
                        raise ValueError
                    dates[field] = date.fromisoformat(row[field])
                except ValueError:
                    error(f"Invalid ISO date: {field}")
            if len(dates) == 2 and dates["edited_at"] < dates["generated_at"]:
                error("Editing predates generation")
            try:
                ref = urlsplit(row["public_clearance_reference"])
                if (ref.scheme != "https" or not ref.hostname or ref.username
                        or ref.password or ref.query or ref.fragment):
                    raise ValueError
            except ValueError:
                error("Clearance reference must be a public HTTPS URL without credentials or query")
            kind = row["asset_kind"]
            if kind not in KINDS:
                error("Unknown asset_kind")
                continue
            counts[kind] += 1
            if kind == "instrumental_excerpt":
                try:
                    duration = Decimal(row["duration_seconds"])
                    if not duration.is_finite() or duration <= 0:
                        raise InvalidOperation
                except InvalidOperation:
                    error("Duration must be finite and positive")
                if row["loudness_normalisation"].casefold() in PLACEHOLDERS:
                    error("Missing loudness normalisation")
            elif row["duration_seconds"] or row["loudness_normalisation"]:
                error("Language bank must not contain audio-only fields")
    if counts["emotion_language_bank"] != 1:
        errors.append("Exactly one frozen language bank required")
    if counts["instrumental_excerpt"] < 2:
        errors.append("At least two instrumental choices required")
    return errors, counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path,
                        default=Path(__file__).with_name("stimulus-manifest.csv"))
    args = parser.parse_args()
    errors, counts = validate_manifest(args.manifest)
    print(f"Metadata counts: {counts}")
    for error in errors:
        print(error, file=sys.stderr)
    print("BLOCKED" if errors else "METADATA VALID ONLY: human review, hash verification and approvals required")
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
