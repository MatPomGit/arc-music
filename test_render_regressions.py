"""Focused E3.1 regression tests, independent of Playwright installation."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import embed_site_assets
from check_public_render import check_identity, check_assets, identity


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


if __name__ == "__main__":
    unittest.main()
