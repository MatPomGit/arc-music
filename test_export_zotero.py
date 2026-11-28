import unittest

from export_zotero import export, parse


def entry(key, title, doi="", extra=""):
    return ("@article{" + key + ", author={Example, A.}, title={" + title +
            "}, year={2026}" + (", doi={" + doi + "}" if doi else "") + extra + "}\n")


class ZoteroExportTests(unittest.TestCase):
    def test_doi_normalization_and_tags(self):
        a = entry("a", "{AI} and music", "https://doi.org/10.1000/ABC")
        b = entry("b", "AI and music", "10.1000/abc", ", pages={1--2}")
        output, conflicts = export([("MSC-MUS-P01", a), ("MSC-MUS-P02", b)])
        self.assertIn("2 source entries; 1 unique records", output)
        self.assertIn("ARC-MUSIC, MSC-MUS-P01, MSC-MUS-P02", output)
        self.assertIn("pages = {1--2}", output)
        self.assertEqual(conflicts, [])

    def test_title_year_and_distinct_dois(self):
        a = entry("a", "{AI} and music")
        b = entry("b", "AI and Music")
        c = entry("a", "AI and Music", "10.1000/one")
        d = entry("a", "AI and Music", "10.1000/two")
        output, _ = export([("MSC-MUS-P01", a), ("MSC-MUS-P02", b),
                            ("MSC-MUS-P03", c), ("MSC-MUS-P04", d)])
        self.assertIn("4 source entries; 3 unique records", output)
        self.assertEqual(len({key for _, key, _ in parse(output)}), 3)

    def test_conflict_report_and_determinism(self):
        a = entry("a", "First", "10.1000/one")
        b = entry("b", "Different", "10.1000/one")
        sources = [("MSC-MUS-P01", a), ("MSC-MUS-P02", b)]
        output, conflicts = export(sources)
        self.assertEqual(export(sources), (output, conflicts))
        self.assertTrue(any("title differs" in c for c in conflicts))
        self.assertIn("title = {First}", output)

    def test_invalid_input_fails(self):
        for value in ("@article{a,title={unclosed}", "@string{a={b}}",
                      "@article{a,title={x},title={y}}"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                list(parse(value))


if __name__ == "__main__":
    unittest.main()
