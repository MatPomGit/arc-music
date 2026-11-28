"""Focused E3.1 regression tests, independent of Playwright installation."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import embed_site_assets
from check_public_render import check_identity, check_assets, identity, visit


class EmbeddingTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "pages").mkdir()
        self.css = self.root / "pages/style.css"
        self.js = self.root / "pages/language.js"
        self.css.write_text("/* zażółć */", encoding="utf-8")
        self.js.write_text("// gęślą", encoding="utf-8")
        mock = patch.object(embed_site_assets, "ROOT", self.root)
        mock.start()
        self.addCleanup(mock.stop)

    def test_exact_utf8(self):
        context = {"keep": True}
        result = embed_site_assets.on_page_context(context)
        self.assertIs(result, context)
        self.assertEqual(result, {"keep": True, "arc_css": "/* zażółć */", "arc_js": "// gęślą"})

    def test_missing_asset(self):
        self.js.unlink()
        with self.assertRaises(FileNotFoundError):
            embed_site_assets.on_page_context({})

    def test_closing_tags(self):
        for path, source in ((self.css, "</StYlE >"), (self.js, "</ScRiPt>")):
            with self.subTest(path=path):
                original = path.read_text(encoding="utf-8")
                path.write_text(source, encoding="utf-8")
                try:
                    with self.assertRaises(ValueError):
                        embed_site_assets.on_page_context({})
                finally:
                    path.write_text(original, encoding="utf-8")


class RoutingTests(unittest.TestCase):
    def page(self, url, lang="pl", section="team", active="team.html"):
        page = Mock(url=url)
        nodes = {"html": Mock(), "body": Mock(), "nav a[aria-current=page]": Mock()}
        for key, value in (("html", lang), ("body", section), ("nav a[aria-current=page]", active)):
            nodes[key].get_attribute.return_value = value
        nodes["nav a[aria-current=page]"].count.return_value = 1
        page.locator.side_effect = nodes.__getitem__
        return page

    def test_valid(self):
        base = "https://example.test/project/"
        check_identity(self.page(base + "team.html"), base, "team.html")
        self.assertEqual(identity(""), ("pl", "index"))
        self.assertEqual(identity("en.html"), ("en", "index"))

    def test_wrong_route(self):
        base = "https://example.test/project/"
        with self.assertRaises(AssertionError):
            check_identity(self.page(base + "team.html"), base, "studies.html")

    def test_wrong_language_section_or_navigation(self):
        base = "https://example.test/project/"
        for kwargs in ({"lang": "en"}, {"section": "index"}, {"active": "index.html"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(AssertionError):
                check_identity(self.page(base + "team.html", **kwargs), base, "team.html")

    def test_navigation_http_status_and_cached_document(self):
        base = "https://example.test/project/"
        for status in (200, 304, 302, 404, 500, None):
            with self.subTest(status=status):
                page = self.page(base + "team.html")
                page.goto.return_value = (None if status is None else
                                          Mock(status=status, ok=200 <= status < 300))
                with patch("check_public_render.check_assets") as assets, \
                     patch("check_public_render.check_render") as render:
                    if status in (200, 304):
                        visit(page, base, "team.html", "css", "js")
                        assets.assert_called_once_with(page, "css", "js")
                        render.assert_called_once_with(page)
                    else:
                        with self.assertRaises(AssertionError):
                            visit(page, base, "team.html", "css", "js")
                        assets.assert_not_called()
                        render.assert_not_called()

    def test_cached_wrong_document_is_rejected(self):
        base = "https://example.test/project/"
        page = self.page(base + "team.html", lang="en")
        page.goto.return_value = Mock(status=304, ok=False)
        with self.assertRaises(AssertionError):
            visit(page, base, "team.html", "css", "js")

    def test_asset_duplicates_and_mismatch(self):
        page = Mock()
        node = page.locator.return_value
        node.count.return_value = 2
        with self.assertRaises(AssertionError):
            check_assets(page, "css", "js")
        node.count.return_value = 1
        node.text_content.return_value = "wrong"
        with self.assertRaises(AssertionError):
            check_assets(page, "css", "js")


class EstimateRegistryTests(unittest.TestCase):
    def fixture(self):
        from check_site_regressions import estimate_text
        registry = {
            "schema": "arc-music-site-estimates-v1",
            "studies": [
                {"id": f"P{i:02d}", "display": {
                    lang: {
                        "sample": f'<p class="pub-sample"><strong>N:</strong> {100*i}</p>',
                        "estimate": f'<p class="pub-estimate"><strong>{lang}:</strong> {1000*i:,} &amp; N={100*i}</p>',
                    } for lang in ("pl", "en")
                }} for i in range(1, 10)
            ],
        }
        def page_for(lang):
            page = Mock()
            nodes = {"html": Mock()}
            nodes["html"].get_attribute.return_value = lang
            for record in registry["studies"]:
                for field in ("sample", "estimate"):
                    selector = f"#msc-mus-{record['id'].lower()} .pub-{field}"
                    node = nodes[selector] = Mock()
                    node.count.return_value = 1
                    node.inner_text.return_value = estimate_text(record["display"][lang][field])
            page.locator.side_effect = nodes.__getitem__
            return page, nodes
        return registry, page_for

    def test_both_languages_and_updated_numbers(self):
        from check_site_regressions import check_rendered_estimates
        registry, page_for = self.fixture()
        for lang in ("pl", "en"):
            page, nodes = page_for(lang)
            check_rendered_estimates(page, registry)
        registry["studies"][0]["display"]["pl"]["sample"] = "<p>N: 5000</p>"
        page, nodes = page_for("pl")
        check_rendered_estimates(page, registry)
        nodes["#msc-mus-p01 .pub-sample"].inner_text.return_value = "N: 420"
        with self.assertRaises(AssertionError):
            check_rendered_estimates(page, registry)

    def test_missing_duplicate_or_changed_content(self):
        from check_site_regressions import check_rendered_estimates
        registry, page_for = self.fixture()
        for count in (0, 2):
            page, nodes = page_for("en")
            nodes["#msc-mus-p09 .pub-estimate"].count.return_value = count
            with self.assertRaises(AssertionError):
                check_rendered_estimates(page, registry)
        page, nodes = page_for("en")
        nodes["#msc-mus-p05 .pub-estimate"].inner_text.return_value = "Changed"
        with self.assertRaises(AssertionError):
            check_rendered_estimates(page, registry)

    def test_entities_and_whitespace(self):
        from check_site_regressions import estimate_text
        self.assertEqual(estimate_text("<p><strong>N:</strong> 54&nbsp;720 000 &amp; 80%\n</p>"),
                         "N: 54 720 000 & 80%")


if __name__ == "__main__":
    unittest.main()


class ManuscriptPreviewTests(unittest.TestCase):
    def fixture(self):
        return "".join(
            f'<article class="pub" id="msc-mus-p{i:02d}" aria-labelledby="msc-mus-p{i:02d}-title">'
            f'<div class="pub-meta">Meta</div><h3 id="msc-mus-p{i:02d}-title">Title</h3>'
            '<p class="pub-question">Question</p><div class="pub-body">Body</div></article>'
            for i in range(1, 10)
        )

    def test_preview_mapping_and_language(self):
        for english, label in ((False, "Otwórz manuskrypt PDF"), (True, "Open manuscript PDF")):
            result = embed_site_assets.add_manuscript_previews(self.fixture(), english)
            self.assertEqual(result.count('class="pub-preview"'), 9)
            self.assertEqual(result.count('loading="eager"'), 9)
            self.assertNotIn('loading="lazy"', result)
            self.assertNotIn('class="pub-authors"', result)
            affiliation = "VIZJA University" if english else "Uniwersytet VIZJA"
            self.assertEqual(result.count(f'<p class="pub-affiliation">{affiliation}</p>'), 9)
            self.assertEqual(result.count('class="pub-body"'), 9)
            self.assertEqual(result.count(label), 18)
            for i in range(1, 10):
                base = f"manuscript-previews/msc-mus-p{i:02d}"
                self.assertEqual(result.count(f'href="{base}.pdf"'), 1)
                self.assertEqual(result.count(f'src="{base}.png"'), 1)

    def test_missing_or_duplicate_panel_rejected(self):
        for malformed in (self.fixture().replace('id="msc-mus-p09"', 'id="wrong"'), self.fixture() * 2):
            with self.assertRaises(ValueError):
                embed_site_assets.add_manuscript_previews(malformed, False)
