import unittest
import numpy as np
from bounded_simulation import bounded
from cluster_calibration import compare
from inference import fit_arrays
class TestClusterCalibration(unittest.TestCase):
    def test_existing_estimator_equivalence(self):
        g,x,y=bounded(np.random.default_rng(16),80,6,.15,.3,"mar")
        a=compare(g,x,y); b=fit_arrays(g,x,y)
        self.assertAlmostEqual(a[0],b["estimate"][0],places=12)
        self.assertAlmostEqual(a[1],b["se"][0],places=12)
        self.assertLess(a[2],a[1])
    def test_invariance(self):
        g,x,y=bounded(np.random.default_rng(18),80,6,.15)
        a=compare(g,x,y); b=compare(g,x,y+g)
        np.testing.assert_allclose(a,b,atol=1e-10)
if __name__=="__main__":unittest.main()
