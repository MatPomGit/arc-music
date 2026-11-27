"""Exact digest verification for public entry points and local CSS/JS."""
import hashlib
from pathlib import Path
import re
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

FILES = (
    "index.html", "en.html", "team.html", "en-team.html", "studies.html",
    "en-studies.html", "publications.html", "en-publications.html",
    "neuropsychology.html", "en-neuropsychology.html",
    "style.css", "language.js", "js/base.js", "js/darkmode.js",
) + tuple(
    f"manuscript-previews/msc-mus-p{i:02d}.{extension}"
    for i in range(1, 10) for extension in ("png", "pdf")
)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def manifest(site, output):
    entries = {name: digest((site / name).read_bytes()) for name in FILES}
    output.write_text("".join(f"{value}  {name}\n" for name, value in entries.items()), encoding="ascii")

def read_manifest(path):
    entries = {}
    for line in path.read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  ([a-z0-9./-]+)", line)
        if not match or match[2] not in FILES or match[2] in entries:
            raise ValueError("Invalid manifest entry")
        entries[match[2]] = match[1]
    if set(entries) != set(FILES):
        raise ValueError("Incomplete manifest")
    return entries

def download(url):
    request = Request(url, headers={"Accept-Encoding": "identity", "Cache-Control": "no-cache"})
    with urlopen(request, timeout=10) as response:
        return response.read()

def verify(entries, base, revision, fetch=download, sleep=time.sleep, attempts=6):
    if not base.startswith("https://") or not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Invalid deployment URL or revision")
    for name, expected in [*entries.items(), ("", entries["index.html"])]:
        url = f"{base.rstrip('/')}/{name}?v={revision}"
        for attempt in range(attempts):
            try:
                actual = digest(fetch(url))
                if actual == expected:
                    break
            except (OSError, URLError):
                pass
            if attempt + 1 < attempts:
                sleep(5)
        else:
            raise RuntimeError(f"FAIL: {name or '/'} differs from build")
        print(f"PASS: {name or '/'} matches deployed build", flush=True)

if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "manifest":
        manifest(Path(sys.argv[2]), Path(sys.argv[3]))
    elif len(sys.argv) == 5 and sys.argv[1] == "verify":
        verify(read_manifest(Path(sys.argv[2])), sys.argv[3], sys.argv[4])
    else:
        raise SystemExit("Usage: verify_public.py manifest SITE OUTPUT | verify MANIFEST URL SHA")
