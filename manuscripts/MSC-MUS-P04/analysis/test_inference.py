import unittest
import numpy as np
from inference import (design,composite,fit_hc3,contrast,target_weights,impute_pmm,
                       pooled_contrast,shift_imputed,analyze)
from simulation import generate,scenario

class InferenceTests(unittest.TestCase):
    def setUp(self):
        self.x,self.y,self.truth=generate(240,.4,"mar",np.random.default_rng(42))
    def test_composite(self):
        self.assertTrue(np.allclose(composite([5,np.nan,np.nan,np.nan],[1,0,1,np.nan]),
                                    [5,0,np.nan,np.nan],equal_nan=True))
        with self.assertRaises(ValueError):
            composite([4],[0])
    def test_standardisation(self):
        self.assertAlmostEqual(self.x[:,2].mean(),0)
        self.assertAlmostEqual(self.x[:,2].std(ddof=1),1)
    def test_hc3_reference(self):
        x,y=self.x,self.y
        good=np.isfinite(y)
        z,t=x[good],y[good]
        b,v,df=fit_hc3(x,y)
        inv=np.linalg.inv(z.T@z)
        hat=z@inv@z.T
        residual=t-z@b
        expected=inv@z.T@np.diag((residual/(1-np.diag(hat)))**2)@z@inv
        np.testing.assert_allclose(v,expected,rtol=1e-10,atol=1e-10)
        np.testing.assert_allclose(b,np.linalg.lstsq(z,t,rcond=None)[0])
    def test_pmm_bounds_and_observed(self):
        d=impute_pmm(self.x,self.y,5,1)
        np.testing.assert_array_equal(d,impute_pmm(self.x,self.y,5,1))
        obs=np.isfinite(self.y)
        np.testing.assert_array_equal(d[:,obs],np.tile(self.y[obs],(5,1)))
        self.assertTrue(np.all((d>=0)&(d<=10)))
        for a in (-.5,.5):
            arm=self.x[:,1]==a
            self.assertTrue(np.isin(d[:,arm],self.y[arm&obs]).all())
    def test_delta_preserves_observed(self):
        d=impute_pmm(self.x,self.y,5,1)
        shifted=shift_imputed(self.x,self.y,d,-2,2,1)
        np.testing.assert_array_equal(shifted[:,np.isfinite(self.y)],d[:,np.isfinite(self.y)])
        np.testing.assert_array_equal(shift_imputed(self.x,self.y,d,0,0,0),d)
    def test_pool_complete(self):
        x,y,_=generate(240,0,"complete",np.random.default_rng(7))
        b,v,df=fit_hc3(x,y); w=target_weights(x)
        q=pooled_contrast(x,impute_pmm(x,y,4,1),w)
        cc=contrast(b,v,df,w)
        self.assertAlmostEqual(q["estimate"],cc["estimate"])
        self.assertAlmostEqual(q["se"],cc["se"])
    def test_full_analysis(self):
        result=analyze(self.x,self.y,m=5)
        self.assertEqual(len(result["sensitivity"]),27)
        zero=[s for s in result["sensitivity"] if s["offset_control"]==s["offset_scaffold"]==s["differential_slope"]==0][0]
        self.assertAlmostEqual(zero["estimate"],result["mar"]["estimate"])
    def test_rank_guard(self):
        with self.assertRaises(ValueError):
            design([0,1],[1,1],np.empty((2,0)))
    def test_simulation_smoke(self):
        s=scenario(240,0,"mar",4,3,7)
        for v in s["methods"].values():
            self.assertEqual(v["valid"],4)
            self.assertEqual(v["failed"],0)

if __name__=="__main__":
    unittest.main()
