"""Check shared research and bilingual numerical reporting contracts (offline)."""
import json
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

def numbers(html,lang):
    text=re.sub(r"<[^>]+>"," ",html)
    if lang=="pl":
        text=re.sub(r"(?<=\d)[ \u00a0\u202f](?=\d{3}(?!\d))","",text)
        text=text.replace(",",".")
    else:
        text=re.sub(r"(?<=\d),(?=\d{3}(?!\d))","",text)
    return Counter(Decimal(x) for x in re.findall(r"(?<![A-Za-z0-9])(?:\d+(?:\.\d+)?|\.\d+)",text))

def panels(text):
    return {i.upper():re.search(r'<p class="pub-estimate">[\s\S]*?</p>',body).group()
            for i,body in re.findall(r'<article class="pub" id="msc-mus-(p0[1-9])"([\s\S]*?)</article>',text)}

def check(root):
    errors=[]
    registry=json.loads((root/"docs/public-estimates.json").read_text(encoding="utf-8"))
    gates=json.loads((root/"docs/research-gates.json").read_text(encoding="utf-8"))
    ids={f"P{i:02}" for i in range(1,10)}
    for rows,key in ((registry["records"],"id"),(gates["studies"],"study")):
        if len(rows)!=9 or {r[key] for r in rows}!=ids:
            errors.append("Research register must contain each P01-P09 once")
    for row in gates["studies"]:
        if not (root/row["contract"]).is_file():
            errors.append("Missing research contract: "+row["study"])
        if row["fieldwork"]!="BLOCKED":
            errors.append("Unapproved fieldwork: "+row["study"])
    for row in registry["records"]:
        for path in row["evidence"]:
            if not (root/path).is_file():
                errors.append("Missing estimate evidence: "+path)
        for ref in row["artifacts"]:
            if not re.fullmatch(r"[a-f0-9]{40}",ref["head"]) or not isinstance(ref["run"],int):
                errors.append("Malformed archival provenance: "+row["id"])
    for lang,name in (("pl","studies.md"),("en","en-studies.md")):
        actual=panels((root/"pages"/name).read_text(encoding="utf-8"))
        if set(actual)!=ids:
            errors.append("Study panel coverage mismatch: "+lang)
        for row in registry["records"]:
            if actual.get(row["id"])!=row[lang]:
                errors.append("Estimate differs from canonical registry: "+row["id"]+" "+lang)
    for row in registry["records"]:
        if numbers(row["pl"],"pl")!=numbers(row["en"],"en"):
            errors.append("Numeric estimate parity mismatch: "+row["id"])
    return errors

if __name__=="__main__":
    root=Path(__file__).resolve().parent
    problems=check(root)
    for p in problems: print("FAIL:",p)
    print("PASS: research registers" if not problems else "FAIL: research registers")
    raise SystemExit(bool(problems))
