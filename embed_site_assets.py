"""Embed trusted local assets in each HTML document to avoid split cache versions."""
from pathlib import Path
import re
import shutil

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


# Only the nine explicitly named manuscript PDFs may enter the public build.
MANUSCRIPTS = tuple(f"MSC-MUS-P{i:02d}" for i in range(1, 10))
PREVIEW_DIR = "manuscript-previews"
AUTHORS = ("Ewa Sterniczuk", "Paulina Ficner", "Cezary Biele", "Mateusz Pomianek")
PANEL = re.compile(
    r'(<article class="pub" id="(msc-mus-p0[1-9])" aria-labelledby="\2-title">\s*)'
    r'(.*?<p class="pub-question">.*?</p>)', re.S
)


def add_manuscript_previews(html, english):
    """Add the same source-derived preview to each localised study panel."""
    found = []

    def replace(match):
        opening, identifier, header = match.groups()
        found.append(identifier.upper())
        label = "Open manuscript PDF" if english else "Otwórz manuskrypt PDF"
        alt = "First page of manuscript" if english else "Pierwsza strona manuskryptu"
        status = "Draft manuscript" if english else "Manuskrypt roboczy"
        path = f"{PREVIEW_DIR}/{identifier}"
        authors_label = "Authors" if english else "Autorzy"
        authors = f'<p class="pub-authors">{authors_label}: {", ".join(AUTHORS)}</p>'
        affiliation = "VIZJA University" if english else "Uniwersytet VIZJA"
        header = header.replace("</h3>", "</h3>" + authors +
                                f'<p class="pub-affiliation">{affiliation}</p>', 1)
        return (
            f'{opening}<div class="pub-header"><div class="pub-heading">{header}</div>'
            f'<figure class="pub-preview"><a href="{path}.pdf" '
            f'aria-label="{label}: {identifier.upper()}">'
            f'<img src="{path}.png" alt="{alt} {identifier.upper()}" '
            f'loading="eager" decoding="async">'
            f'<span>{label}</span></a><figcaption>{status}</figcaption></figure></div>'
        )

    result = PANEL.sub(replace, html)
    if tuple(found) != MANUSCRIPTS:
        raise ValueError(f"Unexpected manuscript panel inventory: {found}")
    return result


def on_page_content(html, page, **kwargs):
    if page.file.src_uri in ("studies.md", "en-studies.md"):
        return add_manuscript_previews(html, page.file.src_uri == "en-studies.md")
    return html


def build_manuscript_previews(root, site_dir):
    """Render the checked-in PDFs without duplicating sources in the repository."""
    import pypdfium2 as pdfium

    destination = Path(site_dir) / PREVIEW_DIR
    destination.mkdir(parents=True, exist_ok=True)
    for identifier in MANUSCRIPTS:
        source = root / "manuscripts" / identifier / "main.pdf"
        if not source.is_file() or source.is_symlink() or source.parent.is_symlink():
            raise ValueError(f"Missing or unsafe manuscript PDF: {identifier}")
        if source.read_bytes()[:5] != b"%PDF-":
            raise ValueError(f"Invalid manuscript PDF: {identifier}")
        basename = identifier.lower()
        document = pdfium.PdfDocument(str(source))
        try:
            if len(document) == 0:
                raise ValueError(f"Empty manuscript PDF: {identifier}")
            page = document[0]
            try:
                bitmap = page.render(scale=1.2)
                try:
                    bitmap.to_pil().save(destination / f"{basename}.png", format="PNG")
                finally:
                    bitmap.close()
            finally:
                page.close()
        finally:
            document.close()
        shutil.copyfile(source, destination / f"{basename}.pdf")


def on_post_build(config, **kwargs):
    build_manuscript_previews(ROOT, config["site_dir"])
