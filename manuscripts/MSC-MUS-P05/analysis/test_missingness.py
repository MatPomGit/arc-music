import unittest
import numpy as np
from missingness import simulate_selection,propensity,weighted_moments,selection_fit
from ordinal_cfa import pair_moments

class MissingnessTests(unittest.TestCase):
    def test_equal_weights(self):
        y,_,_,_=simulate_selection(600,2,4,.65,.3,"MAR",.2,np.random.default_rng(42))
        a=weighted_moments(y,np.ones(len(y))); b=pair_moments(y)
        np.testing.assert_allclose(a[0],b[0],atol=1e-6)
        np.testing.assert_allclose(a[2],b[2],atol=1e-10)
    def test_mar_propensity(self):
        _,x,z,truth=simulate_selection(5000,2,4,.65,.3,"MAR",.25,np.random.default_rng(52))
        estimated=propensity(x,z)
        self.assertLess(np.max(abs(estimated-truth)),.05)
    def test_mnar_not_mar(self):
        _,x,z,truth=simulate_selection(1000,2,4,.65,.3,"MNAR",.25,np.random.default_rng(9))
        missing=~np.isfinite(x).all(axis=1)
        self.assertTrue(np.isnan(x[missing,:4]).all())
        self.assertGreater(np.ptp(truth[z[:,0]==0]),.15)
    def test_tilt_direction(self):
        _,x,z,_=simulate_selection(1500,2,4,.65,.3,"MNAR",.25,np.random.default_rng(82))
        d=np.repeat(np.arange(2),4)
        fits=[selection_fit(x,z,d,delta=v) for v in (-1.,0.,1.)]
        self.assertTrue(all(f.ess<=f.complete_n+1e-9 for f in fits))
        self.assertGreater(fits[0].fit.thresholds[0,1],fits[2].fit.thresholds[0,1])
    def test_invalid_probability(self):
        _,x,z,_=simulate_selection(500,2,4,.65,.3,"MAR",.2,np.random.default_rng(42))
        with self.assertRaises(ValueError):
            selection_fit(x,z,np.repeat(np.arange(2),4),prob=np.zeros(len(x)))

if __name__=="__main__":
    unittest.main()
