import itertools
import unittest
import numpy as np
from extended_calibration import outcome_bounds,run
from inference import fit_arrays

class ExtendedCalibrationTests(unittest.TestCase):
    def test_bounds_exhaustive(self):
        rng=np.random.default_rng(42)
        g=np.repeat(np.arange(12),4)
        x=np.column_stack([np.tile([0,1,0,1],12),rng.normal(size=48)])
        y=rng.integers(0,11,48).astype(float)
        seen=np.ones(48,bool);seen[[0,5,12]]=False
        upper=np.full(48,10.)
        lo,hi=outcome_bounds(g,x,y,seen,upper)
        vals=[]
        for v in itertools.product((0.,10.),repeat=3):
            filled=y.copy();filled[~seen]=v
            vals.append(fit_arrays(g,x,filled)["beta"])
        self.assertAlmostEqual(lo,min(vals),places=10)
        self.assertAlmostEqual(hi,max(vals),places=10)
        lo,hi=outcome_bounds(g,x,y,np.ones(48,bool),upper)
        self.assertAlmostEqual(lo,fit_arrays(g,x,y)["beta"],places=10)
        self.assertAlmostEqual(hi,lo,places=10)
    def test_smoke(self):
        r=run(reps=2,seed=5,smoke=True)
        self.assertTrue(r["complete"])
        self.assertEqual(len(r["cells"]),2)
        for c in r["cells"]:
            for m in c["models"].values():
                self.assertEqual(m["valid"]+m["failed"],2)
                self.assertEqual(m["bounds_valid"],2)

    def test_selected_cell_matches_smoke_seed(self):
        smoke=run(reps=2,seed=5,smoke=True)
        self.assertEqual(smoke["full_grid_indices"],[0,71])
        selected=run(reps=2,seed=5,cell_index=71)
        self.assertEqual(selected["cells"][0],smoke["cells"][-1])
        self.assertTrue(selected["screening_only"])
        with self.assertRaises(ValueError):
            run(reps=2,cell_index=72)
        with self.assertRaises(ValueError):
            run(reps=2,smoke=True,cell_index=0)
