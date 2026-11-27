"""Offline consistency checks for prospective P02 source."""
from pathlib import Path
import re

root = Path(__file__).resolve().parent
seen = set()
active = set()


def expand(path):
    path = path.resolve()
    assert path.is_relative_to(root) and path.is_file(), path
    assert path not in active and path not in seen, f"Repeated or cyclic input: {path}"
    active.add(path)
    seen.add(path)
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"\\input\{([^}]+)\}", lambda m: expand(root / m.group(1)), text)
    active.remove(path)
    return text


body = expand(root / "main.tex")
bib = (root / "references.bib").read_text(encoding="utf-8")
keys = re.findall(r"@\w+\{([^,]+),", bib)
used = {k.strip() for group in re.findall(r"\\(?:citep|citet|cite)\{([^}]+)\}", body) for k in group.split(",")}
assert len(keys) == len(set(keys)) and set(keys) == used, (set(keys)-used, used-set(keys))
dois = re.findall(r"doi\s*=\s*\{([^}]+)\}", bib, flags=re.I)
assert len(dois) == len({d.casefold() for d in dois}), "duplicate DOI"
assert re.findall(r"\\item\[RQ(\d)\.\]", body) == list("12345")
assert r"\section{Results}" not in body
assert "No participant data have yet been collected or analysed." in body
assert body.index(r"\subsection{Episode selection and interview comparability}") < body.index(r"\subsection{Interview guide}")
assert "Context and alternatives &" in body
guide = (root / "interview-guide-pl.md").read_text(encoding="utf-8")
minutes = [int(x) for x in re.findall(r"\|\s*(\d+) min\s*\|", guide)]
assert len(minutes) == 9 and sum(minutes) == 60, minutes
assert "ostatniej kwalifikującej się sesji" in guide and "Kontekst i alternatywy" in guide
assert all((root / p).is_file() for p in ("publication.md","source-readiness.md","fieldwork-protocol-pl.md","analysis-records.md"))
register = (root / "citation-register.md").read_text(encoding="utf-8")
registered = re.findall(r"^\| ([a-z]+\d{4}) \|", register, flags=re.M)
assert len(registered) == len(set(registered)) and set(registered) == set(keys), (set(keys)-set(registered), set(registered)-set(keys))
assert (root / "independent-review-handoff.md").is_file()

# P02 corpus and artefact contract.
field=(root / "fieldwork-protocol-pl.md").read_text(encoding="utf-8")
assert "The corpus of interviews is the unit of thematic analysis" in body
assert "not independent observations" in body
assert "Showing is not consent to capture" in body
assert "Korpus wywiadów jest jednostką analizy" in field and "Korpus wywiadów jest jednostką analizy" in guide
assert "Nie wymagać powodu" in field and "Nie żądać powodu" in guide
assert "zatrzymać nagrywanie i transkrypcję" in field
assert "Zgoda na rozmowę lub pokaz nie jest zgodą" in guide

# Prospective pilot and analytic-transfer contract.
assert r'\subsection{Pilot and fieldwork decision rules}' in body
assert r'\label{fig:episode-elicitation}' in body
assert r'\subsection{From extracts to an interpretive account}' in body
assert 'hypothetical illustration, not a result of P02' in body
records=(root/'analysis-records.md').read_text(encoding='utf-8')
assert '| Pilot review |' in records and '| Construct transfer |' in records
assert 'wersja 0.3.0' in guide and 'Procedura terenowa 0.3.0' in field

# Ethics preparation is explicitly prospective.
ethics_draft=(root/'ethics-preparation-pl.md').read_text(encoding='utf-8')
assert 'NO-GO dla rekrutacji i pilotażu' in ethics_draft
assert 'NIEZWERYFIKOWANE' in ethics_draft
assert 'does not constitute institutional approval' in body

# Capture controls must be applied before any interview, not afterwards.
pre_interview = re.search(r"^## Przed rozmową\s*\n(.*?)(?=^## |\Z)", field, flags=re.M | re.S)
assert pre_interview, "Missing pre-interview procedure"
for control in ("nieautoryzowanych asystentów spotkań", "zewnętrzną transkrypcję", "automatyczną synchronizację"):
    assert control in pre_interview.group(1), f"Missing pre-interview capture control: {control}"
assert re.search(r"wyłączyć[^.]*nieautoryzowanych asystentów spotkań", pre_interview.group(1), re.I), "Capture controls must be disabled before interviewing"

print(f"PASS: P02 protocol, {len(seen)} LaTeX files, 5 research questions, {len(keys)} matched references, 60-minute guide")
