import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from verify_public import FILES, digest, manifest, read_manifest, verify

class VerifyPublicTests(unittest.TestCase):
    def test_manifest_covers_assets_and_rejects_incomplete_or_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in FILES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(name.encode())
            out = root / "manifest"
            manifest(root, out)
            self.assertEqual(read_manifest(out), {n: digest(n.encode()) for n in FILES})
            original = out.read_text()
            for broken in (original.splitlines()[0] + "\n", original + original.splitlines()[0] + "\n"):
                out.write_text(broken)
                with self.assertRaises(ValueError):
                    read_manifest(out)

    def test_root_and_asset_retry(self):
        entries = {n: digest(n.encode()) for n in FILES}
        counts = {}
        def fetch(url):
            name = urlsplit(url).path.removeprefix("/project/")
            counts[name] = counts.get(name, 0) + 1
            if name in ("", "style.css") and counts[name] == 1:
                return b"stale"
            return (name or "index.html").encode()
        verify(entries, "https://example.invalid/project/", "a"*40, fetch=fetch, sleep=lambda _: None)
        self.assertEqual(counts[""], 2)
        self.assertEqual(counts["style.css"], 2)

    def test_asset_mismatch_fails(self):
        entries = {n: digest(n.encode()) for n in FILES}
        def fetch(url):
            name = urlsplit(url).path.removeprefix("/project/")
            return b"stale" if name == "language.js" else name.encode()
        with self.assertRaisesRegex(RuntimeError, "language.js"):
            verify(entries, "https://example.invalid/project/", "a"*40, fetch=fetch, sleep=lambda _: None, attempts=2)

if __name__ == "__main__":
    unittest.main()
