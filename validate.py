"""Offline checks for concise documentation and isolated site sources."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
LIMITS = {
    "README.md": 2000, "AGENTS.md": 2000,
    "docs/aim-er.md": 3000, "docs/first-study.md": 4000,
    "docs/data-policy.md": 2000,
}
PUBLIC = {"index.md", "team.md", "studies.md", "en.md"}
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
    if entries != PUBLIC:
        errors.append("Unexpected or missing public files")
    for name in PUBLIC:
        path = folder / name
        if path.is_file() and not path.is_symlink():
            body = path.read_text(encoding="utf-8")
            if FORBIDDEN.search(body):
                errors.append(f"Unsafe public content: {name}")
            for target in re.findall(r"\]\(([^)]+)\)", body):
                if target not in PUBLIC:
                    errors.append(f"Unapproved public link: {name}")
    config = (root / "mkdocs.yml").read_text(encoding="utf-8")
    keys = [line.split(":", 1)[0].strip() for line in config.splitlines()
            if line and not line.startswith((" ", "#"))]
    if set(keys) != {"site_name", "docs_dir", "site_dir", "theme", "nav"} or len(keys) != 5:
        errors.append("Unexpected site configuration")
    if not re.search(r"(?m)^docs_dir: pages$", config) or not re.search(r"(?m)^site_dir: site$", config):
        errors.append("Site source/output boundary changed")
    if not re.search(r"(?m)^  highlightjs: false$", config):
        errors.append("Remote highlighter must be disabled")
    nav = re.findall(r"(?m)^  - [^:]+: ([a-z.]+)$", config)
    if set(nav) != PUBLIC or len(nav) != len(PUBLIC):
        errors.append("Public navigation mismatch")
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
