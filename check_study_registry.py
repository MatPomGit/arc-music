"""Validate bilingual public estimates against one versioned registry."""
import collections
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def numeric_tokens(html, lang):
    s=re.sub(r"<[^>]+>","",html)
    s=re.sub(r"\bH[0-9]+\b","",s)
    s=re.sub(r"(?<=\d) (?=\d{3}(?:\D|$))" if lang=="pl" else r"(?<=\d),(?=\d{3}(?:\D|$))","",s)
    if lang=="pl":s=re.sub(r"(?<=\d),(?=\d)",".",s)
    return collections.Counter(float(x) for x in re.findall(r"\d+(?:\.\d+)?|\.\d+",s))

def validate(root=ROOT):
    data=json.loads((root/"pages/study-estimates.json").read_text(encoding="utf-8"))
    assert data["schema"]=="arc-music-site-estimates-v1"
    assert [r["id"] for r in data["studies"]]==[f"P{i:02d}" for i in range(1,10)]
    pages={l:(root/"pages"/n).read_text(encoding="utf-8") for l,n in (("pl","studies.md"),("en","en-studies.md"))}
    for record in data["studies"]:
        for key in ("estimand","method","design","status","evidence"):
            assert record[key], (record["id"],key)
        for ref in [record["evidence"],*record.get("additional_evidence",[])]:
            assert (root/ref).is_file(),ref
        if record["sha"] is not None:assert re.fullmatch(r"[a-f0-9]{40}",record["sha"])
        for lang,content in pages.items():
            panel=re.search(r'<article class="pub" id="msc-mus-'+record["id"].lower()+r'"[\s\S]*?</article>',content).group()
            for field in ("sample","estimate"):
                actual=re.search(r'<p class="pub-'+field+r'">[\s\S]*?</p>',panel).group()
                assert actual==record["display"][lang][field],(record["id"],lang,field)
        assert numeric_tokens(record["display"]["pl"]["estimate"],"pl")==numeric_tokens(record["display"]["en"]["estimate"],"en"),record["id"]
    for id,pl,en in (("P08","NO-GO","NO-GO"),("P09","nie daje testu potwierdzającego","cannot provide confirmatory tests")):
        row=next(r for r in data["studies"] if r["id"]==id)
        assert pl in row["display"]["pl"]["estimate"] and en in row["display"]["en"]["estimate"]

if __name__=="__main__":
    validate()
    print("All 9 bilingual public estimate records match canonical registry and numeric parity")
