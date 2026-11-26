import unittest
import numpy as np
from completion_calibration import generate, observe, conditional_means, status_informed_pmm, scenario, METHODS

class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.x,self.low,self.high,self.meaningful,self.mu=generate(300,.54,"status_dependent",np.random.default_rng(42))
    def test_exact_truth(self):
        self.assertAlmostEqual(np.linalg.lstsq(self.x,self.mu,rcond=None)[0][3],.54)
        p,mu,f=conditional_means(self.x,.54)
        np.testing.assert_allclose(p*f,mu)
        self.assertGreater(np.std(p),.01)
        self.assertGreater(abs(np.corrcoef(self.x[:,2],self.x[:,4])[0,1]),.3)
    def test_observe(self):
        y,s=observe(np.array([False,True,False,True]),np.array([4,5,6,7]),
                    np.array([False,False,False,True]),np.array([True,True,False,False]))
        np.testing.assert_allclose(y,[0,np.nan,np.nan,7],equal_nan=True)
        np.testing.assert_allclose(s,[0,1,np.nan,1],equal_nan=True)
    def test_enhanced_monotone(self):
        y,s=self.low; z,t=self.high
        known=np.isfinite(s)
        np.testing.assert_array_equal(s[known],t[known])
        observed=np.isfinite(y)
        np.testing.assert_array_equal(y[observed],z[observed])
        self.assertLessEqual(np.isnan(z).sum(),np.isnan(y).sum())
        self.assertLessEqual(np.isnan(t).sum(),np.isnan(s).sum())
    def test_status_donors(self):
        y,s=self.low
        draws=status_informed_pmm(self.x,y,s,5,13)
        np.testing.assert_array_equal(draws,status_informed_pmm(self.x,y,s,5,13))
        obs=np.isfinite(y)
        np.testing.assert_array_equal(draws[:,obs],np.tile(y[obs],(5,1)))
        for arm in (-.5,.5):
            a=self.x[:,1]==arm
            missing=a&(s==1)&np.isnan(y)
            self.assertTrue(np.isin(draws[:,missing],y[a&(s==1)&obs]).all())
        self.assertTrue(np.all((draws>=0)&(draws<=10)))
    def test_invalid_status(self):
        y,s=self.low
        s=s.copy()
        s[np.flatnonzero(np.isfinite(y)&(y>0))[0]]=0
        with self.assertRaises(ValueError):
            status_informed_pmm(self.x,y,s,3,1)
    def test_smoke(self):
        s=scenario(300,0,"outcome_dependent",3,3,7)
        self.assertEqual(s["paired_valid"],3)
        for name in METHODS:
            self.assertEqual(s["methods"][name]["valid"],3)
            self.assertEqual(s["methods"][name]["failed"],0)
            self.assertLessEqual(s["methods"][name]["grid_robust_rejection"],s["methods"][name]["nominal_rejection"])

if __name__=="__main__":
    unittest.main()
