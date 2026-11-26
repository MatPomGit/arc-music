"""Isolate template lifecycle fixtures from the configured research programme."""
import json
import shutil
import tempfile
from functools import lru_cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_TEMP = tempfile.TemporaryDirectory(prefix="arc-template-test-")

@lru_cache(maxsize=1)
def template_root():
    root = Path(_TEMP.name) / "arc"
    shutil.copytree(REPO, root, ignore=shutil.ignore_patterns(
        ".git", ".venv", "site", "__pycache__", "manuscripts", "research"))
    snapshot = json.loads((REPO / "tests" / "fixtures" / "empty_template.json").read_text(encoding="utf-8"))
    for rel, content in snapshot.items():
        (root / rel).write_text(content, encoding="utf-8")
    for rel in ("team.md", "studies.md", "en.md"):
        (root / "pages" / rel).unlink(missing_ok=True)
    return root
