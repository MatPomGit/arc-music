import unittest
import numpy as np
from ordinal_imputation import impute,rubin_pool,fit_multiple
from missingness import simulate_selection

class ImputationTests(unittest.TestCase):
    def setUp(self):
        _,self.x,self.z,_=simulate_selection(300,2,3,.65,.3,"MAR",.2,np.random.default_rng(42))
    def test_preservation_and_seed(self):
        a,_=impute(self.x,self.z,m=3,sweeps=8,gibbs_steps=2,seed=8)
        b,_=impute(self.x,self.z,m=3,sweeps=8,gibbs_steps=2,seed=8)
        obs=np.isfinite(self.x)
        for i,j in zip(a,b):
            np.testing.assert_array_equal(i,j)
            np.testing.assert_array_equal(i[obs],self.x[obs])
            self.assertTrue(np.isin(i,np.arange(5)).all())
        self.assertFalse(np.array_equal(a[0],a[1]))
    def test_delta(self):
        a,_=impute(self.x,self.z,m=2,sweeps=12,gibbs_steps=3,delta=-1,seed=8)
        b,_=impute(self.x,self.z,m=2,sweeps=12,gibbs_steps=3,delta=1,seed=8)
        mask=np.isnan(self.x)
        self.assertLess(np.mean([v[mask].mean() for v in a]),np.mean([v[mask].mean() for v in b]))
    def test_rubin(self):
        out=rubin_pool([[1.,2.],[3.,4.]],[np.eye(2),np.eye(2)])
        np.testing.assert_allclose(out["estimates"],[2,3])
        np.testing.assert_allclose(out["covariance"],[[4,3],[3,4]])
        np.testing.assert_allclose(out["df"],[16/9,16/9])
    def test_zero_between(self):
        out=rubin_pool([[1.],[1.]],[[[.25]],[[.25]]])
        self.assertTrue(np.isinf(out["df"][0]))
        self.assertAlmostEqual(out["intervals"][0,0],.020018,places=5)
    def test_invalid(self):
        with self.assertRaises(ValueError):
            impute(self.x,self.z,m=1)
        with self.assertRaises(ValueError):
            rubin_pool([[1.],[2.]],[[[-1]],[[1]]])
    def test_fit_accounting(self):
        out=fit_multiple(self.x,self.z,np.repeat(np.arange(2),3),m=3,sweeps=10,gibbs_steps=3,seed=9)
        self.assertEqual(out["proper"]+sum(out["failures"].values()),3)
        if out["pooled"] is not None:
            self.assertEqual(out["pooled"]["estimates"].shape,(7,))

if __name__=="__main__":
    unittest.main()
