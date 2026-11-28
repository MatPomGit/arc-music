"""Deterministic Zotero export from the nine canonical manuscript bibliographies.

The supported source dialect uses brace-delimited values, including nested
LaTeX braces. Unsupported BibTeX constructs fail rather than losing metadata.
Deduplication is DOI-first; records without DOI use normalized title and year.
Conflicting nonempty fields are reported, not asserted to be verified.
"""
import argparse
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parent
HEADER = "% ARC-MUSIC | AIM-ER | Generated from canonical P01-P09 references.bib\n"


def normalize(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value).lower()
                   if c.isalnum())


def doi(value):
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "",
                  value.strip(), flags=re.I).lower()


def parse(source):
    """Yield (type, key, fields), preserving raw LaTeX field values."""
    starts = list(re.finditer(r"(?m)^[ \t]*@(\w+)\s*\{\s*([^,\n]+),", source))
    if not starts:
        raise ValueError("No bibliography entries")
    if len(re.findall(r"(?m)^[ \t]*@", source)) != len(starts):
        raise ValueError("Unsupported bibliography directive")
    for n, match in enumerate(starts):
        end = starts[n+1].start() if n+1 < len(starts) else len(source)
        raw = source[match.end():end]
        fields = {}
        pos = 0
        while True:
            while pos < len(raw) and (raw[pos].isspace() or raw[pos] == ","):
                pos += 1
            if pos < len(raw) and raw[pos] == "}":
                rest = raw[pos+1:]
                if re.sub(r"(?m)^[ \t]*%[^\n]*", "", rest).strip():
                    raise ValueError("Unexpected text after entry: " + match[2])
                break
            field = re.match(r"(\w+)\s*=\s*\{", raw[pos:])
            if not field:
                raise ValueError("Expected brace-delimited field in " + match[2])
            name = field[1].lower()
            pos += field.end()
            start = pos
            depth = 1
            while pos < len(raw) and depth:
                ch = raw[pos]
                if ch == "\\" and pos+1 < len(raw):
                    pos += 2
                    continue
                depth += (ch == "{") - (ch == "}")
                pos += 1
            if depth:
                raise ValueError("Unbalanced field in " + match[2])
            if name in fields:
                raise ValueError("Duplicate field " + name + " in " + match[2])
            fields[name] = raw[start:pos-1]
            while pos < len(raw) and raw[pos].isspace():
                pos += 1
            if pos >= len(raw) or raw[pos] not in ",}":
                raise ValueError("Missing field delimiter in " + match[2])
        yield match[1].lower(), match[2].strip(), fields


def export(sources):
    groups = {}
    count = 0
    conflicts = []
    for study, source in sources:
        local_keys = set()
        for kind, key, raw in parse(source):
            count += 1
            if key.lower() in local_keys:
                raise ValueError(f"{study}: duplicate key {key}")
            local_keys.add(key.lower())
            fields = dict(raw)
            if "journaltitle" in fields and "journal" not in fields:
                fields["journal"] = fields.pop("journaltitle")
            if "eid" in fields and "pages" not in fields:
                fields["pages"] = fields["eid"]
            if not fields.get("title") or not fields.get("author") or not (fields.get("year") or fields.get("date")):
                raise ValueError(f"{study}: incomplete entry {key}")
            identifier = doi(fields.get("doi", ""))
            if identifier:
                fields["doi"] = identifier
                identity = ("doi", identifier)
            else:
                identity = ("title", normalize(fields["title"]),
                            fields.get("year", fields.get("date", ""))[:4])
            tags = [v.strip() for v in fields.pop("keywords", "").split(",") if v.strip()]
            if identity not in groups:
                groups[identity] = [kind, key, fields, set(), set()]
            row = groups[identity]
            row[3].add(study)
            row[4].update(tags)
            if row[0] != kind:
                conflicts.append(f"{key}: entry type differs")
            for name, value in fields.items():
                previous = row[2].get(name)
                if not previous:
                    row[2][name] = value
                elif normalize(previous) != normalize(value):
                    conflicts.append(f"{key}: {name} differs in {study}")
    seen = set()
    records = []
    for kind, key, fields, studies, tags in groups.values():
        outkey = key
        if outkey.lower() in seen:
            base = key + "-" + min(studies).split("-")[-1].lower()
            outkey = base
            n = 2
            while outkey.lower() in seen:
                outkey = f"{base}-{n}"
                n += 1
        seen.add(outkey.lower())
        fields["keywords"] = ", ".join(["ARC-MUSIC", *sorted(studies),
                                         *sorted(tags - {"ARC-MUSIC"} - studies)])
        body = ",\n".join(f"  {name} = {{{value}}}" for name, value in sorted(fields.items()))
        records.append((outkey.lower(), f"@{kind}{{{outkey},\n{body}\n}}\n"))
    header = HEADER + f"% {count} source entries; {len(records)} unique records.\n"
    header += "% Metadata inherited; conflicting fields retain first nonempty value. Not a source verification.\n\n"
    return header + "\n".join(v for _, v in sorted(records)), conflicts


def generate(root=ROOT):
    sources = []
    for i in range(1, 10):
        study = f"MSC-MUS-P{i:02}"
        path = root / "manuscripts" / study / "references.bib"
        sources.append((study, path.read_text(encoding="utf-8")))
    return export(sources)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output, conflicts = generate()
    for conflict in conflicts:
        print("Metadata review:", conflict, file=sys.stderr)
    path = ROOT / "docs" / "arc-music-zotero.bib"
    if args.check:
        if path.read_text(encoding="utf-8") != output:
            print("FAIL: Zotero export is stale", file=sys.stderr)
            return 1
    else:
        path.write_text(output, encoding="utf-8")
    print("PASS: Zotero bibliography")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
