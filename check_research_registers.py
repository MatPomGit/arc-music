"""Validate cross-study consent and data contracts without exposing any raw data."""
import json
from pathlib import Path
from check_study_registry import validate

def check(root):
    errors=[]
    gates=json.loads((root/"docs/research-gates.json").read_text(encoding="utf-8"))
    ids={f"P{i:02}" for i in range(1,10)}
    if len(gates["studies"])!=9 or {r["study"] for r in gates["studies"]}!=ids:
        errors.append("Research register must contain each P01-P09 once")
    for row in gates["studies"]:
        if not (root/row["contract"]).is_file():
            errors.append("Missing research contract: "+row["study"])
        if row["fieldwork"]!="BLOCKED":
            errors.append("Unapproved fieldwork: "+row["study"])
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
