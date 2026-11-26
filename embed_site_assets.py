"""Embed trusted local assets in each HTML document to avoid split cache versions."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def on_page_context(context, **kwargs):
    for name, filename, closing_tag in (
        ("arc_css", "style.css", "</style"),
        ("arc_js", "language.js", "</script"),
    ):
        source = (ROOT / "pages" / filename).read_text(encoding="utf-8")
        if closing_tag in source.lower():
            raise ValueError(f"Unsafe closing tag in {filename}")
        context[name] = source
    return context
