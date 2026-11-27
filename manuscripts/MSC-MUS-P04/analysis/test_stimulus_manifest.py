"""Synthetic tests only; no actual stimuli or clearance assertions."""
import csv
from pathlib import Path
import tempfile
import unittest

from stimulus_manifest import FIELDS, validate_manifest


class StimulusManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "manifest.csv"

    def rows(self):
        rows = []
        for i, kind in enumerate(("instrumental_excerpt", "instrumental_excerpt",
                                  "emotion_language_bank"), 1):
            rows.append(dict(zip(FIELDS, (
                f"synthetic-{i}", kind, "v1", "synthetic fixture", "fixture", "1",
                "2026-01-01", "2026-01-02", "30" if i < 3 else "",
                "fixture procedure" if i < 3 else "", "synthetic fixture only",
                "https://example.invalid/fixture", str(i) * 64,
            ))))
        return rows

    def write(self, rows):
        with self.path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def test_header_only_blocked(self):
        self.write([])
        errors, counts = validate_manifest(self.path)
        self.assertTrue(errors)
        self.assertEqual(sum(counts.values()), 0)

    def test_valid_synthetic_metadata(self):
        self.write(self.rows())
        errors, counts = validate_manifest(self.path)
        self.assertEqual(errors, [])
        self.assertEqual(counts["instrumental_excerpt"], 2)

    def test_invalid_values_blocked(self):
        for field, value in (("duration_seconds", "NaN"),
                             ("sha256", "invalid"),
                             ("rights_basis", "pending"),
                             ("edited_at", "2025-01-01"),
                             ("public_clearance_reference", "https://example.invalid/?token=x"),
                             ("model_version", "")):
            with self.subTest(field=field):
                rows = self.rows()
                rows[0][field] = value
                self.write(rows)
                self.assertTrue(validate_manifest(self.path)[0])

    def test_duplicate_and_bank_contract(self):
        rows = self.rows()
        rows[1]["asset_id"] = rows[0]["asset_id"]
        rows[1]["sha256"] = rows[0]["sha256"]
        rows[2]["duration_seconds"] = "30"
        self.write(rows)
        errors, _ = validate_manifest(self.path)
        self.assertTrue(any("Duplicate asset_id" in e for e in errors))
        self.assertTrue(any("Duplicate asset hash" in e for e in errors))
        self.assertTrue(any("audio-only" in e for e in errors))

    def test_wrong_header(self):
        self.path.write_text("asset_id,unknown\nx,y\n", encoding="utf-8")
        self.assertTrue(validate_manifest(self.path)[0])


if __name__ == "__main__":
    unittest.main()
