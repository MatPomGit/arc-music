import unittest
import numpy as np
from robust_cfa import robust_moments,robust_fit,_model_jacobian
from recovery import simulate

class RobustTests(unittest.TestCase):
    def test_jacobian(self):
        d=np.repeat(np.arange(2),3); l=np.linspace(.5,.8,6)
        phi=np.array([[1,.3],[.3,1.]])
        pred,J=_model_jacobian(l,phi,d)
        for k in range(7):
            ll=l.copy(); pp=phi.copy()
            if k<6: ll[k]+=1e-6
            else: pp[0,1]+=1e-6; pp[1,0]+=1e-6
            new,_=_model_jacobian(ll,pp,d)
            np.testing.assert_allclose((new-pred)/1e-6,J[:,k],atol=1e-8)
    def test_influence_leave_one_out(self):
        x=simulate(1500,2,3,.65,.3,False,0.,np.random.default_rng(42))
        m=robust_moments(x[:,:2])
        self.assertAlmostEqual(m.influence[:,0].mean(),0.,places=10)
        for index in (0,10,20,30):
            loo=robust_moments(np.delete(x[:,:2],index,axis=0))
            actual=(len(x)-1)*(m.correlations[0]-loo.correlations[0])
            self.assertAlmostEqual(actual,m.influence[index,0],delta=.04)
    def test_fit(self):
        d=np.repeat(np.arange(2),4)
        x=simulate(1200,2,4,.65,.3,False,0.,np.random.default_rng(51))
        fit=robust_fit(x,d)
        self.assertTrue(fit.fit.proper)
        self.assertEqual(fit.nominal_df,19)
        self.assertEqual(fit.intervals.shape,(9,2))
        self.assertGreater(np.linalg.eigvalsh(fit.covariance)[0],0.)
        self.assertLess(np.max(np.abs(fit.parameters-np.r_[np.full(8,.65),.3])),.14)
        self.assertTrue(0<=fit.p_value<=1)
        self.assertGreater(fit.effective_df,0)
    def test_missing_rejected(self):
        x=simulate(500,2,3,.65,.3,False,0.,np.random.default_rng(42))
        x[0,0]=np.nan
        with self.assertRaises(ValueError):
            robust_moments(x)

if __name__=="__main__":
    unittest.main()
