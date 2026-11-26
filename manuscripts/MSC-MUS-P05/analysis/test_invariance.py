import unittest
import numpy as np
from invariance import contrasts,compare_groups,wald
from recovery import simulate

class InvarianceTests(unittest.TestCase):
    def test_exact_affine_link(self):
        d=np.repeat(np.arange(2),4)
        l1=np.linspace(.5,.75,8)
        sd_factor=np.array([1.3,.8])[d]
        mu=np.array([.35,-.4])[d]
        scale=np.sqrt(l1*l1*sd_factor**2+1-l1*l1)
        l2=l1*sd_factor/scale
        t1=np.tile([-.9,-.3,.2,.85],(8,1))
        t2=(t1-(l1*mu)[:,None])/scale[:,None]
        a=np.r_[l1,t1.ravel()]; b=np.r_[l2,t2.ravel()]
        np.testing.assert_allclose(contrasts(a,b,d),0,atol=1e-12)
        # Standardized loadings and thresholds differ even under invariance.
        self.assertGreater(np.max(abs(l1-l2)),.05)
        t2[2,1]+=.15
        self.assertGreater(np.max(abs(contrasts(a,np.r_[l2,t2.ravel()],d)[:16])),.05)
    def test_loading_violation(self):
        d=np.repeat(np.arange(2),4); l=np.full(8,.65)
        t=np.tile([-.9,-.3,.2,.85],(8,1))
        a=np.r_[l,t.ravel()]; b=a.copy(); b[2]=.45
        c=contrasts(a,b,d)
        np.testing.assert_allclose(c[:16],0)
        self.assertGreater(np.max(abs(c[16:22])),.2)
    def test_wald(self):
        out=wald([0.,0.],np.eye(2))
        self.assertEqual(out["p_value"],1.)
        with self.assertRaises(ArithmeticError):
            wald([1.,1.],np.ones((2,2)))
    def test_group_fit_and_gate(self):
        rng=np.random.default_rng(42); d=np.repeat(np.arange(2),4)
        x=simulate(800,2,4,.65,.3,False,0.,rng)
        y=simulate(800,2,4,.65,.3,False,0.,rng)
        out=compare_groups(x,y,d)
        self.assertEqual(out["tests"]["threshold_loading_intercept"]["df"],28)
        self.assertFalse(out["latent_mean_comparison_authorized"])
        self.assertTrue(all(0<=v["p_value"]<=1 for v in out["tests"].values()))
        with self.assertRaises(ValueError):
            compare_groups(x[:100],y,d)

if __name__=="__main__":
    unittest.main()
