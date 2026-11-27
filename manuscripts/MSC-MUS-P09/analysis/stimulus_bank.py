"""Validate a frozen P09 stimulus manifest; no generators, downloads or licences inferred."""
import hashlib
import json
import re
from pathlib import Path

FIELDS = {"id","modality","filename","sha256","provenance","rights_basis","approval_ref"}
TOP = {"version","purpose","stimuli"}
ID = re.compile(r"(music|visual)-[1-6]")
HEX = re.compile(r"[0-9a-f]{64}")


def validate_manifest(manifest, directory, *, allow_synthetic=False):
    if set(manifest) != TOP or not isinstance(manifest["version"], str) or not manifest["version"].strip():
        raise ValueError("Invalid manifest schema")
    purpose = manifest["purpose"]
    if purpose != "approved-study" and not (purpose == "synthetic-test" and allow_synthetic):
        raise ValueError("Stimulus bank not authorised for requested use")
    if not isinstance(manifest["stimuli"], list) or len(manifest["stimuli"]) != 12:
        raise ValueError("Exactly six stimuli per modality required")
    root = Path(directory).resolve(strict=True)
    ids, files, digests = set(), set(), set()
    for entry in manifest["stimuli"]:
        if set(entry) != FIELDS or any(not isinstance(v,str) or not v.strip() for v in entry.values()):
            raise ValueError("Incomplete stimulus provenance")
        ident = entry["id"]
        if not ID.fullmatch(ident) or entry["modality"] != ident.split("-")[0]:
            raise ValueError("Invalid modality or identifier")
        file = Path(entry["filename"])
        if file.name != entry["filename"] or file.is_absolute() or file.name in (".",".."):
            raise ValueError("Unsafe stimulus filename")
        allowed = {".wav",".mp3",".ogg"} if entry["modality"]=="music" else {".png",".jpg",".webp"}
        if file.suffix.lower() not in allowed:
            raise ValueError("Invalid media extension")
        path = root / file
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing or linked stimulus")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if not HEX.fullmatch(entry["sha256"]) or digest != entry["sha256"]:
            raise ValueError("Stimulus digest mismatch")
        if ident in ids or file.name in files or digest in digests:
            raise ValueError("Duplicate stimulus")
        ids.add(ident); files.add(file.name); digests.add(digest)
    if ids != {f"{m}-{i}" for m in ("music","visual") for i in range(1,7)}:
        raise ValueError("Incomplete modality bank")
    # Canonical ordering makes manifest digest independent of input row order.
    canonical = dict(manifest, stimuli=sorted(manifest["stimuli"],key=lambda x:x["id"]))
    return hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(",",":"),
                                     ensure_ascii=False).encode()).hexdigest()
