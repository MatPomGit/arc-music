import tempfile
import unittest
from pathlib import Path
import numpy as np
from reproduce import compare_rows
from bootstrap_calibration import dataset,run
class TestReproduction(unittest.TestCase):
    def test_rounding_and_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"table.csv"
            p.write_text("n,mechanism,bias\n80,mar,.0123\n",encoding="utf-8")
            self.assertEqual(compare_rows(p,[dict(n=80,mechanism="mar",bias=.01234)],["n","mechanism"])["mismatch_count"],0)
            self.assertEqual(compare_rows(p,[dict(n=80,mechanism="mar",bias=.0124)],["n","mechanism"])["mismatch_count"],1)
            self.assertEqual(compare_rows(p,[],["n","mechanism"])["mismatch_count"],1)
    def test_dataset_reproducibility(self):
        a=dataset(np.random.default_rng(42),40,6,.15,.3,"mar")
        b=dataset(np.random.default_rng(42),40,6,.15,.3,"mar")
        self.assertTrue(a.equals(b))
        self.assertTrue(a.interference.isna().any())
    def test_bootstrap_smoke(self):
        r=run(reps=1,bootstrap=3,reference_n=500,n=40,seed=12)
        self.assertTrue(r["screening_only"])
        self.assertEqual(len(r["cells"]),6)
        self.assertTrue(all(c["valid"]+c["failures"]==1 for c in r["cells"]))
if __name__=="__main__":unittest.main()
