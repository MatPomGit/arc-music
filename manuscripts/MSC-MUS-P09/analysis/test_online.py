import hashlib
import random
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from export_schema import FIELDS,VERSION
from test_inference import fixture
from inference import analyze,prepare
import pandas as pd
from allocation import allocate, ledger, withdraw, assert_active, reconcile, record_checkpoint
from stimulus_bank import validate_manifest
from task import start, transition, summary


class AllocationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name)/"p09.sqlite"
        self.bank = "a"*64

    def assign(self, i, training=0, **kwargs):
        gates = dict(eligible=True, consented=True, baseline_complete=True)
        gates.update(kwargs)
        return allocate(self.path, f"{i:032x}", training, self.bank, **gates)

    def test_gates_and_retry(self):
        with self.assertRaises(ValueError):
            self.assign(1, consented=False)
        self.assertFalse(self.path.exists())
        a = self.assign(1)
        self.assertEqual(a,self.assign(1))
        self.assertEqual(set(a),{"music","randomised_at","bank_digest","schema_version"})
        with self.assertRaises(ValueError):
            self.assign(1,1)
        self.bank = "b"*64
        with self.assertRaises(ValueError):
            self.assign(2)

    def test_balance(self):
        rng = random.Random(42)
        for i in range(101):
            self.assign(i,i%2,rng=rng)
        with sqlite3.connect(self.path) as db:
            for s in (0,1):
                arms = [r[0] for r in db.execute("SELECT music FROM slots WHERE training=? ORDER BY id",(s,))]
                self.assertEqual(arms.count(0),arms.count(1))
                used = db.execute("SELECT s.music FROM slots s JOIN assignments a ON s.id=a.slot WHERE s.training=?",(s,)).fetchall()
                self.assertLessEqual(abs(sum(2*r[0]-1 for r in used)),3)

    def test_concurrent_retries_and_distinct(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            same = list(pool.map(lambda _: self.assign(1),range(16)))
            list(pool.map(self.assign,range(2,34)))
        self.assertTrue(all(x==same[0] for x in same))
        self.assertEqual(len(ledger(self.path)),33)

    def test_checkpoint_withdrawal_serialization(self):
        for i in range(1, 13):
            self.assign(i)
            pid = f"{i:032x}"
            def write():
                try:
                    record_checkpoint(self.path, pid, "task_started")
                    return True
                except ValueError:
                    return False
            with ThreadPoolExecutor(max_workers=2) as pool:
                writer = pool.submit(write)
                cessation = pool.submit(withdraw, self.path, pid)
                accepted = writer.result()
                cessation.result()
            with self.assertRaises(ValueError):
                record_checkpoint(self.path, pid, "t1_submitted")
            with sqlite3.connect(self.path) as db:
                exists = db.execute("SELECT name FROM sqlite_master WHERE name='checkpoints'").fetchone()
                count = db.execute("SELECT count(*) FROM checkpoints WHERE participant_id=?", (pid,)).fetchone()[0] if exists else 0
            self.assertEqual(count, int(accepted))

    def test_reconciliation_and_cessation(self):
        self.assign(1); self.assign(2,1)
        data = pd.DataFrame(ledger(self.path))
        self.assertEqual(reconcile(self.path,data,strict=False),2)
        with self.assertRaises(ValueError):
            reconcile(self.path,data.iloc[:1],strict=False)
        corrupted = data.copy()
        corrupted.loc[0,"music"] = 1-corrupted.loc[0,"music"]
        with self.assertRaises(ValueError):
            reconcile(self.path,corrupted,strict=False)
        assert_active(self.path,f"{1:032x}")
        withdraw(self.path,f"{1:032x}")
        withdraw(self.path,f"{1:032x}")
        with self.assertRaises(ValueError):
            assert_active(self.path,f"{1:032x}")
        with self.assertRaises(ValueError):
            self.assign(1)
        with self.assertRaises(ValueError):
            reconcile(self.path,data,strict=False)

    def test_strict_export_and_ordering(self):
        import csv
        with patch("allocation.now",return_value="2026-11-01T10:00:00+00:00"):
            self.assign(1);self.assign(2,1);self.assign(3)
        pid=f"{1:032x}"
        with patch("allocation.now",return_value="2026-11-01T10:00:01Z"):
            for stage in ("task_finished","t1_submitted"):
                with self.assertRaises(ValueError):record_checkpoint(self.path,pid,stage)
            first=record_checkpoint(self.path,pid,"task_started")
            self.assertEqual(record_checkpoint(self.path,pid,"task_started"),first)
            with self.assertRaises(ValueError):record_checkpoint(self.path,pid,"task_finished")
        with patch("allocation.now",return_value="2026-11-01T10:08:01Z"):
            record_checkpoint(self.path,pid,"task_finished")
            with self.assertRaises(ValueError):record_checkpoint(self.path,pid,"task_stopped")
        with patch("allocation.now",return_value="2026-11-01T10:09:00Z"):
            record_checkpoint(self.path,pid,"t1_submitted")
        pid2=f"{2:032x}"
        with patch("allocation.now",return_value="2026-11-01T10:00:01Z"):
            record_checkpoint(self.path,pid2,"task_started")
            record_checkpoint(self.path,pid2,"task_stopped")
            record_checkpoint(self.path,pid2,"t1_submitted")
        with patch("allocation.now",return_value="2026-11-08T10:00:00Z"):
            record_checkpoint(self.path,f"{3:032x}","t2_submitted")
        d=pd.DataFrame(ledger(self.path)).drop(columns="withdrawn")
        f=fixture().iloc[:3].reset_index(drop=True)
        for k in FIELDS:
            if k not in d:d[k]=f[k]
        for j in (1,2):
            cols=[f"same_event{j}",*[f"understanding{j}{k}" for k in (1,2,3)]]
            if j==1:cols.append("distance1")
            d.loc[d[f"t{j}_at"].isna(),cols]=None
        self.assertEqual(set(d),set(FIELDS))
        with open(Path(__file__).with_name("data-dictionary.csv"),newline="") as file:
            self.assertEqual({row["field"] for row in csv.DictReader(file)},set(FIELDS))
        self.assertEqual(reconcile(self.path,d),3)
        self.assertEqual(analyze(d)["randomised"],3)
        self.assertEqual(int(prepare(d).valid1.sum()),2)
        self.assertEqual(int(prepare(d).valid2.sum()),1)
        for field,value in (("bank_digest","bad"),("bank_digest","b"*64),("schema_version","old"),("task_end_reason","task_stopped"),("t1_at","2026-11-01T10:00:02Z")):
            bad=d.copy();bad.loc[0,field]=value
            with self.assertRaises(ValueError):reconcile(self.path,bad)
        with self.assertRaises(ValueError):reconcile(self.path,d.drop(columns="bank_digest"))
        d.loc[0,"t1_at"]="2026-11-01T11:09:00+01:00"
        self.assertEqual(reconcile(self.path,d),3)


class BankTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.manifest = dict(version="fixture-1",purpose="synthetic-test",stimuli=[])
        for m,ext in (("music","wav"),("visual","png")):
            for i in range(1,7):
                ident = f"{m}-{i}"
                name = f"{ident}.{ext}"
                content = ident.encode()
                (self.root/name).write_bytes(content)
                self.manifest["stimuli"].append(dict(id=ident,modality=m,filename=name,
                    sha256=hashlib.sha256(content).hexdigest(),provenance="synthetic bytes, not media",
                    rights_basis="test fixture only",approval_ref="test only"))

    def test_synthetic_blocked_and_digest_order(self):
        with self.assertRaises(ValueError):
            validate_manifest(self.manifest,self.root)
        digest = validate_manifest(self.manifest,self.root,allow_synthetic=True)
        self.manifest["stimuli"].reverse()
        self.assertEqual(digest,validate_manifest(self.manifest,self.root,allow_synthetic=True))

    def test_corruption_and_path(self):
        entry = self.manifest["stimuli"][0]
        (self.root/entry["filename"]).write_bytes(b"corrupt")
        with self.assertRaises(ValueError):
            validate_manifest(self.manifest,self.root,allow_synthetic=True)
        entry["filename"] = "../music-1.wav"
        with self.assertRaises(ValueError):
            validate_manifest(self.manifest,self.root,allow_synthetic=True)


class TaskTests(unittest.TestCase):
    def test_identical_contract(self):
        for arm in (0,1):
            t = start(arm)
            with self.assertRaises(ValueError):
                transition(t,"select",1,2)
            t = transition(t,"preview",10,2)
            t = transition(t,"select",20,2)
            t = transition(t,"preview",25,3)
            t = transition(t,"select",40,3)
            t = transition(t,"finish",480)
            self.assertTrue(summary(t)["completed"])
            self.assertEqual(summary(t)["selected"],3)
            with self.assertRaises(ValueError):
                transition(t,"preview",480,1)

    def test_stop_and_no_selection(self):
        t = transition(start(0),"stop",10)
        self.assertFalse(summary(t)["completed"])
        with self.assertRaises(ValueError):
            transition(t,"preview",11,1)
        self.assertFalse(summary(transition(start(1),"finish",480))["completed"])
        with self.assertRaises(ValueError):
            transition(start(0),"preview",float("nan"),1)


if __name__ == "__main__":
    unittest.main()
