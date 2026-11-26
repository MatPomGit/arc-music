"""Checks of the actual ARC-MUSIC programme, not an empty template."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_repository import validate
from validate_documentation import check_documentation
from validate_pages import check_pages

class MusicProgrammeTests(unittest.TestCase):
    def test_programme_contract(self):
        self.assertEqual([], validate(ROOT, verified_repository="MatPomGit/arc-music"))
        self.assertEqual([], check_documentation(ROOT))

    def test_isolated_pages_and_private_data(self):
        self.assertEqual([], check_pages(ROOT))
        meta = json.loads((ROOT / "program.json").read_text())
        self.assertEqual("private", meta["repository_visibility"])
        self.assertEqual("Ewa Sterniczuk", meta["owner"])
        self.assertFalse(meta["owner_of_raw_data"])
        for f in (ROOT / "pages").rglob("*.md"):
            self.assertNotIn("sharepoint.com", f.read_text().lower())
            self.assertNotIn("github.com/matpomgit/", f.read_text().lower())

    def test_canonical_latex_registry(self):
        records = json.loads((ROOT / "portfolio/papers.json").read_text())["papers"]
        self.assertGreaterEqual(len(records), 10)
        for record in records:
            with self.subTest(id=record["id"]):
                self.assertEqual("local", record["owner"]["mode"])
                self.assertEqual("MatPomGit/arc-music", record["owner"]["repository"])
                self.assertFalse(record["public_listing"])
                self.assertEqual("latex", record["manuscript"]["format"])
                self.assertTrue((ROOT / record["manuscript"]["path"]).is_file())

if __name__ == "__main__":
    unittest.main()
