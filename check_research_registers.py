"""Validate cross-study consent and data contracts without exposing any raw data."""
import json
import re
from pathlib import Path
from check_study_registry import validate

def check(root):
    errors=[]
    gates=json.loads((root/"docs/research-gates.json").read_text(encoding="utf-8"))
    ids={f"P{i:02}" for i in range(1,10)}
    if len(gates["studies"])!=9 or {r["study"] for r in gates["studies"]}!=ids:
        errors.append("Research register must contain each P01-P09 once")
    for row in gates["studies"]:
        for contract in [row["contract"],*row.get("additional_contracts",[])]:
            if not (root/contract).is_file() or not (root/contract).resolve().is_relative_to(root.resolve()):
                errors.append("Missing or unsafe research contract: "+row["study"]+": "+contract)
        if row["fieldwork"]!="BLOCKED":
            errors.append("Unapproved fieldwork: "+row["study"])
    matrix=root/"docs/research-matrix.md"
    content=matrix.read_text(encoding="utf-8")
    rows=re.findall(r"^\| \[(P\d{2})\]\(([^)]+)\) /",content,re.M)
    if [r[0] for r in rows]!=sorted(ids):
        errors.append("Research matrix must contain each P01-P09 once in order")
    for study,link in rows:
        expected=root/"manuscripts"/("MSC-MUS-"+study)/"main.tex"
        if (matrix.parent/link).resolve()!=expected.resolve() or not expected.is_file():
            errors.append("Invalid study matrix manuscript link: "+study)
    if gates.get("status")=="PROSPECTIVE_NO_GO":
        common=gates.get("common",{})
        if common.get("recruitment")!="BLOCKED" or common.get("raw_records_in_git") is not False:
            errors.append("Invalid prospective recruitment/data gate")
    mapfile=root/"manuscripts/MSC-MUS-P01/analysis/proposition-map.md"
    content=mapfile.read_text(encoding="utf-8")
    rows=[line.split("|")[1:-1] for line in content.splitlines()
          if re.match(r"^\| (CP|H\d+) \|",line)]
    if [r[0].strip() for r in rows]!=["CP",*[f"H{i}" for i in range(1,11)]]:
        errors.append("Incomplete AIM-ER proposition map")
    for row in rows:
        if len(row)!=6 or any(not v.strip() for v in row):
            errors.append("Incomplete AIM-ER proposition row: "+row[0])
        elif not row[4].strip().startswith(("PARTIAL","UNTESTED","EXACT")):
            errors.append("Unknown AIM-ER mapping status: "+row[0])
    for link in re.findall(r"\]\((\.\./\.\./[^)]+)\)",content):
        if not (mapfile.parent/link).resolve().is_file():
            errors.append("Broken AIM-ER mapping link: "+link)
    try:
        validate(root)
    except (AssertionError,ValueError,AttributeError,KeyError,OSError) as exc:
        errors.append("Public estimate register: "+str(exc))
    return errors

if __name__=="__main__":
    problems=check(Path(__file__).resolve().parent)
    for problem in problems: print("FAIL:",problem)
    print("PASS: research registers" if not problems else "FAIL: research registers")
    raise SystemExit(bool(problems))
