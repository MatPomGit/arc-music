"""Fail closed on absent PDF or unresolved reference/citation diagnostics."""
import argparse
from pathlib import Path
import re
import tempfile

UNRESOLVED = re.compile(
    r"(?:citation|reference)[^\n]*undefined|undefined (?:references|citations)|"
    r"undefined control sequence|(?:LaTeX|Package [^\n]+) Error:", re.I)


def check(pdf, log):
    pdf, log = Path(pdf), Path(log)
    if not pdf.is_file() or pdf.stat().st_size < 100 or not pdf.read_bytes().startswith(b"%PDF-"):
        raise ValueError("Missing or invalid PDF")
    if not log.is_file() or not log.stat().st_size:
        raise ValueError("Missing or empty compile log")
    text = log.read_text(encoding="utf-8", errors="replace")
    match = UNRESOLVED.search(text)
    if match:
        raise ValueError("Unresolved diagnostic: "+match.group(0))
    return True


def self_test():
    with tempfile.TemporaryDirectory() as temp:
        pdf, log = Path(temp)/"main.pdf", Path(temp)/"main.log"
        pdf.write_bytes(b"%PDF-1.5\n"+b" "*100)
        log.write_text("Output written successfully.",encoding="utf-8")
        assert check(pdf,log)
        for text in ("LaTeX Warning: Citation 'missing' on page 1 undefined",
                     "LaTeX Warning: There were undefined references.",
                     "! Undefined control sequence.",
                     "Package biblatex Error: Invalid citation."):
            log.write_text(text,encoding="utf-8")
            try:
                check(pdf,log)
            except ValueError:
                continue
            raise AssertionError("Invalid log accepted")
        pdf.unlink()
        try:
            check(pdf,log)
        except ValueError:
            return
        raise AssertionError("Absent PDF accepted")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("pdf",nargs="?")
    p.add_argument("log",nargs="?")
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:
        self_test()
    elif a.pdf and a.log:
        check(a.pdf,a.log)
    else:
        p.error("provide PDF and log or --self-test")
    print("PASS")
