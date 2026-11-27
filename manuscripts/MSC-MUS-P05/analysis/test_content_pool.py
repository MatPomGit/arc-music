"""Check integrity of the two unvalidated content-pool versions."""
import csv
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "instrument"


def read(name):
    with (ROOT / name).open(encoding="utf-8",newline="") as stream:
        return list(csv.DictReader(stream))


class ContentPoolTests(unittest.TestCase):
    def test_candidate_and_trace(self):
        old = read("item-pool-pl.csv")
        new = read("item-pool-v0.2.0-pl.csv")
        trace = read("item-revision-v0.2.0.csv")
        self.assertEqual(len(old),35)
        self.assertEqual(len(new),35)
        self.assertEqual(len(trace),35)
        self.assertEqual(len({x["item_id"] for x in new}),35)
        changes = set()
        for a,b,t in zip(old,new,trace):
            self.assertEqual((a["item_id"],a["domain"]),(b["item_id"],b["domain"]))
            self.assertEqual((a["item_id"],a["domain"]),(t["item_id"],t["domain"]))
            self.assertEqual(a["wording"],t["original_wording"])
            self.assertEqual(b["wording"],t["candidate_wording"])
            self.assertEqual(b["status"],"candidate")
            self.assertEqual(t["p02_status"],"oczekuje_na_P02")
            self.assertEqual(t["p02_theme_id"],"")
            self.assertEqual(t["expert_status"],"oczekuje")
            self.assertEqual(t["cognitive_status"],"oczekuje")
            if a["wording"] != b["wording"]:
                changes.add(a["item_id"])
        self.assertEqual(changes, {"EXP02","EXP03","EXP04","MOD02","MOD03","MOD05",
                                  "PER01","PER02","PER03","PER04","PER05","AVO04"})
