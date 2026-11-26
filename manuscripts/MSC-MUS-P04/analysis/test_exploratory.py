import unittest
import numpy as np
from exploratory import spline_sensitivity, rcs
from inference import robustness_label

class ExploratoryTests(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(92); n=200
        self.a=np.arange(n)%2
        self.d=rng.integers(6,43,n).astype(float)
        self.c=np.column_stack((rng.uniform(0,10,(n,3)),rng.integers(0,2,(n,2))))
        self.y=np.clip(5+.3*self.a+.1*self.d+rng.normal(0,2,n),0,10)
        self.y[:10]=np.nan
    def test_invalid_total(self):
        self.d[0]=43
        with self.assertRaises(ValueError):
            spline_sensitivity(self.a,self.d,self.c,self.y,m=3)
    def test_rcs_linear_tails(self):
        self.assertEqual(rcs(-2,[-1,0,1]),0)
        self.assertAlmostEqual(rcs(4,[-1,0,1])-rcs(3,[-1,0,1]),
                               rcs(3,[-1,0,1])-rcs(2,[-1,0,1]))
        with self.assertRaises(ValueError):
            rcs(0,[0,0,1])
    def test_spline(self):
        out=spline_sensitivity(self.a,self.d,self.c,self.y,m=3)
        self.assertEqual(len(out["knots"]),3)
        self.assertEqual(set(out["assignment_contrasts"]),{"-1.0","0.0","1.0"})
        self.assertTrue(np.isfinite(out["nonlinear_interaction"]["estimate"]))
    def test_robust_label(self):
        pos={"lower":.01,"upper":1}; neg={"lower":-1,"upper":-.01}; zero={"lower":-1,"upper":1}
        self.assertEqual(robustness_label(pos,[pos]*27),"ROBUST_POSITIVE")
        self.assertEqual(robustness_label(neg,[neg]*27),"ROBUST_NEGATIVE")
        self.assertEqual(robustness_label(pos,[pos]*26+[zero]),"SENSITIVITY_DEPENDENT_POSITIVE")
        self.assertEqual(robustness_label(zero,[pos]*27),"INCONCLUSIVE")
        with self.assertRaises(ValueError):
            robustness_label(pos,[pos])

if __name__=="__main__":
    unittest.main()
