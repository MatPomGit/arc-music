"""Offline consistency checks for prospective P02 source."""
from pathlib import Path
import re

root = Path(__file__).resolve().parent
main = (root / "main.tex").read_text(encoding="utf-8")
files = [root / name for name in re.findall(r"\\input\{([^}]+)\}", main)]
files.append(root / "sections/interview.tex")
assert all(p.is_file() for p in files), files
body = main + "\n" + "\n".join(p.read_text(encoding="utf-8") for p in files)
bib = (root / "references.bib").read_text(encoding="utf-8")
keys = re.findall(r"@\w+\{([^,]+),", bib)
used = {k.strip() for group in re.findall(r"\\(?:citep|citet|cite)\{([^}]+)\}", body) for k in group.split(",")}
assert len(keys) == len(set(keys)) and set(keys) == used, (set(keys)-used, used-set(keys))
assert len(re.findall(r"\\item\[RQ\d\.\]", body)) == 5
assert r"\section{Results}" not in body
assert "No participant data have yet been collected or analysed." in body
assert all((root / p).is_file() for p in ("publication.md","interview-guide-pl.md","source-readiness.md"))
print(f"PASS: P02 protocol, 5 research questions, {len(keys)} matched references")
