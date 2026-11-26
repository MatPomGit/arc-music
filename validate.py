"""Offline checks for concise documentation and isolated site sources."""
from pathlib import Path
import hashlib
import re
import sys

ROOT = Path(__file__).resolve().parent
LIMITS = {
    "README.md": 2000, "AGENTS.md": 2000,
    "docs/aim-er.md": 3000, "docs/first-study.md": 4000,
    "docs/data-policy.md": 2000,
}
PUBLIC = {"index.md", "team.md", "studies.md", "publications.md", "en.md",
          "en-team.md", "en-studies.md", "en-publications.md",
          "neuropsychology.md", "en-neuropsychology.md"}
ASSETS = {"language.js", "style.css"}
REFERENCES = {
    "https://doi.org/10.1038/nrn3666",
    "https://doi.org/10.1038/nn.2726",
    "https://doi.org/10.1111/j.1467-9280.2007.01916.x",
    "https://doi.org/10.1093/cercor/bhp008",
    "https://doi.org/10.1177/03057356231212362",
    "https://doi.org/10.3389/fnhum.2026.1967909",
}
FORBIDDEN = re.compile(
    r"\b(?:AGENTS\.md|TODO|FIXME|PLACEHOLDER|TBD|REPLACE_[A-Z0-9_]+)\b"
    r"|uwagi?\s+redakcyjne|instrukcj\w*\s+dla\s+agent\w*"
    r"|system prompt|developer instructions|editorial notes?"
    r"|sharepoint\.com|onedrive|github\.com/matpomgit|\.\./|file://"
    r"|<\s*/?\s*(?:script|iframe|object|embed|form|base)\b|\bon[a-z]+\s*=",
    re.I,
)

def check(root=ROOT):
    errors = []
    limits = dict(LIMITS)
    limits.update({f"pages/{name}": 2000 for name in PUBLIC})
    for path in (root / "docs").glob("*.md"):
        limits.setdefault(path.relative_to(root).as_posix(), 4000)
    for name, limit in sorted(limits.items()):
        path = root / name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root.parent):
            errors.append(f"Unsafe documentation path: {name}")
        elif not path.is_file():
            errors.append(f"Missing documentation: {name}")
        elif len(path.read_text(encoding="utf-8")) > limit:
            errors.append(f"Character limit exceeded: {name}")
    folder = root / "pages"
    if not folder.is_dir() or folder.is_symlink():
        return errors + ["Unsafe or missing public source directory"]
    entries = {p.relative_to(folder).as_posix() for p in folder.rglob("*")}
    if entries != PUBLIC | ASSETS:
        errors.append("Unexpected or missing public files")
    for name in PUBLIC:
        path = folder / name
        if path.is_file() and not path.is_symlink():
            body = path.read_text(encoding="utf-8")
            if FORBIDDEN.search(body):
                errors.append(f"Unsafe public content: {name}")
            for target in re.findall(r"\]\(([^)]+)\)", body):
                if target not in PUBLIC and not (name in {"neuropsychology.md", "en-neuropsychology.md"} and target in REFERENCES):
                    errors.append(f"Unapproved public link: {name}")
    config = (root / "mkdocs.yml").read_text(encoding="utf-8")
    keys = [line.split(":", 1)[0].strip() for line in config.splitlines()
            if line and not line.startswith((" ", "#"))]
    if set(keys) != {"site_name", "docs_dir", "site_dir", "use_directory_urls",
                     "theme", "plugins", "extra_javascript", "extra_css", "nav"} or len(keys) != 9:
        errors.append("Unexpected site configuration")
    if not re.search(r"(?m)^docs_dir: pages$", config) or not re.search(r"(?m)^site_dir: site$", config):
        errors.append("Site source/output boundary changed")
    if not re.search(r"(?m)^  highlightjs: false$", config):
        errors.append("Remote highlighter must be disabled")
    for setting in ("use_directory_urls: false", "  color_mode: auto",
                    "  user_color_mode_toggle: true", "  - language.js", "  - style.css", "plugins: []"):
        if setting not in config.splitlines():
            errors.append(f"Missing site setting: {setting}")
    nav = re.findall(r"(?m)^  - [^:]+: ([a-z.-]+)$", config)
    if set(nav) != PUBLIC or len(nav) != len(PUBLIC):
        errors.append("Public navigation mismatch")
    pairs = (("index.md", "en.md"), ("team.md", "en-team.md"),
             ("studies.md", "en-studies.md"), ("publications.md", "en-publications.md"),
             ("neuropsychology.md", "en-neuropsychology.md"))
    for pl, en in pairs:
        for name in (pl, en):
            path = folder / name
            if path.is_file() and not path.is_symlink():
                if f"[PL]({pl}) · [EN]({en})" not in path.read_text(encoding="utf-8"):
                    errors.append(f"Missing reciprocal language switch: {name}")
    asset = folder / "language.js"
    if not asset.is_file() or asset.is_symlink():
        errors.append("Missing or unsafe language script")
    elif re.search(r"https?://|\bfetch\s*\(|XMLHttpRequest|\beval\s*\(", asset.read_text(encoding="utf-8")):
        errors.append("Language script must be local and offline")
    stylesheet = folder / "style.css"
    if not stylesheet.is_file() or stylesheet.is_symlink():
        errors.append("Missing or unsafe stylesheet")
    elif re.search(r"https?://|@import\b|url\s*\(", stylesheet.read_text(encoding="utf-8"), re.I):
        errors.append("Stylesheet must use local assets")
    # Protect the current tree, not historical Git objects or external access.
    private_url = re.compile(
        r"https?://[^\s<>\x22\x27]*(?:sharepoint\.com|onedrive\.live\.com|1drv\.ms|discord\.gg)",
        re.I,
    )
    approved_shortcut = "docs/BazaDanychOneDrive.desktop"
    shortcut_blob = "9dea9bf85b3da7dc7385e4292a284fc28d8cb46c"
    candidates = [root / "README.md", root / "AGENTS.md", root / "LICENSE"]
    for directory in ("docs", "manuscripts", "pages"):
        candidates.extend((root / directory).rglob("*"))
    for path in candidates:
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            errors.append(f"Unsafe linked path: {relative}")
        elif relative == approved_shortcut:
            # Exact user-approved institutional shortcut; no authorization check here.
            if not path.is_file():
                errors.append(f"Invalid institutional shortcut: {relative}")
            else:
                data = path.read_bytes()
                blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\x00" + data).hexdigest()
                if blob != shortcut_blob:
                    errors.append(f"Unreviewed institutional shortcut: {relative}")
        elif path.suffix.lower() in {".desktop", ".url"}:
            errors.append(f"Private shortcut prohibited: {relative}")
        elif path.is_file() and (path.suffix.lower() in {".md", ".tex", ".bib", ".txt", ".yaml", ".yml", ".json", ".py", ".csv"} or path.name == "LICENSE"):
            if private_url.search(path.read_text(encoding="utf-8")):
                errors.append(f"Private access link prohibited: {relative}")
    manuscripts = root / "manuscripts"
    if not manuscripts.is_dir() or manuscripts.is_symlink():
        return errors + ["Unsafe or missing manuscripts directory"]
    folders = sorted(manuscripts.iterdir())
    if not folders:
        errors.append("No manuscript directories")
    for item in folders:
        if not item.is_dir() or item.is_symlink() or not re.fullmatch(r"MSC-MUS-P\d{2}", item.name):
            errors.append(f"Invalid manuscript directory: {item.name}")
            continue
        source = item / "main.tex"
        target = item / "publication.md"
        if not source.is_file() or source.is_symlink():
            errors.append(f"Missing or unsafe LaTeX source: {item.name}")
        if not target.is_file() or target.is_symlink():
            errors.append(f"Missing or unsafe publication plan: {item.name}")
            continue
        content = target.read_text(encoding="utf-8")
        if len(content) > 500:
            errors.append(f"Publication plan exceeds 500 characters: {item.name}")
        primary = re.findall(r"(?m)^\*\*Czasopismo docelowe:\*\* ([^\n]+)$", content)
        alternative = re.findall(r"(?m)^\*\*Czasopismo alternatywne:\*\* ([^\n]+)$", content)
        if (len(primary) != 1 or len(alternative) != 1
                or not primary[0].strip() or not alternative[0].strip()
                or primary[0].strip().casefold() == alternative[0].strip().casefold()):
            errors.append(f"Invalid publication targets: {item.name}")
    return errors

if __name__ == "__main__":
    try:
        problems = check()
    except (OSError, UnicodeError) as exc:
        problems = [str(exc)]
    for problem in problems:
        print("FAIL:", problem)
    print("PASS: ARC-MUSIC" if not problems else "FAIL: ARC-MUSIC")
    sys.exit(bool(problems))
