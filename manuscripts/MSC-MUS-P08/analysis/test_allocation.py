import unittest,tempfile,random,sqlite3
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from allocation import allocate
class TestAllocation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"test.sqlite"
    def test_idempotent(self):
        a=allocate(self.path,"p",0,random.Random(1))
        self.assertEqual(a,allocate(self.path,"p",0,random.Random(2)))
        with self.assertRaisesRegex(ValueError,"changed"):allocate(self.path,"p",1)
    def test_strata_and_blocks(self):
        rng=random.Random(12)
        for i in range(72):
            allocate(self.path,str(i),i%2,rng)
        with sqlite3.connect(self.path) as db:
            for s in (0,1):
                counts=Counter(db.execute("SELECT authority,manual FROM slots WHERE training=?",(s,)).fetchall())
                self.assertEqual(len(counts),4);self.assertEqual(len(set(counts.values())),1)
                used=Counter(db.execute("SELECT authority,manual FROM slots JOIN assignments ON slots.id=assignments.slot WHERE training=?",(s,)).fetchall())
                self.assertLessEqual(max(used.values())-min(used.values()),3)
    def test_concurrent_retries(self):
        with ThreadPoolExecutor(max_workers=8) as ex:
            results=list(ex.map(lambda _:allocate(self.path,"same",1),range(16)))
        self.assertTrue(all(r==results[0] for r in results))
        with sqlite3.connect(self.path) as db:self.assertEqual(db.execute("SELECT count(*) FROM assignments").fetchone()[0],1)
    def test_invalid_input(self):
        with self.assertRaises(ValueError):allocate(self.path,"",0)
        with self.assertRaises(ValueError):allocate(self.path,"p",2)
if __name__=="__main__":unittest.main()
