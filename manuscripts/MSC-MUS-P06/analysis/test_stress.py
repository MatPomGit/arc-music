import unittest
import numpy as np
from stress import draw,fit,run
from inference import fit_arrays
class TestStress(unittest.TestCase):
    def test_equivalence(self):
        g,x,y,_=draw(np.random.default_rng(42),80,6,.15,.3,"mar",.4)
        a=fit(g,x,y); b=fit_arrays(g,x,y)
        self.assertAlmostEqual(a[0],b["estimate"][0],places=12)
        self.assertAlmostEqual(a[1],b["se"][0],places=12)
    def test_monotone(self):
        g,x,y,r=draw(np.random.default_rng(5),160,10,.15,.45,"mnar",.7)
        for i in np.unique(g):
            days=x[g==i,3]
            np.testing.assert_array_equal(days,np.arange(1,len(days)+1))
        self.assertTrue(.35<r<.75)
    def test_reproducibility(self):
        a=run(seed=4,reps=2,reference_n=500)
        b=run(seed=4,reps=2,reference_n=500)
        self.assertEqual(a,b)
        self.assertEqual(len(a["cells"]),36)
if __name__=="__main__": unittest.main()
