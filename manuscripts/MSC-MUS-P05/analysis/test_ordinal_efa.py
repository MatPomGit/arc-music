import unittest
import numpy as np
from scipy.stats import multivariate_normal
from ordinal_efa import rectangle_prob, polychoric_pair, polychoric_matrix, parallel_analysis, minres_promax
from recovery import simulate, run, recover

class OrdinalTests(unittest.TestCase):
    def test_rectangle_reference(self):
        a=np.array([-.8,-.2,.3,.9]); b=np.array([-1.,-.3,.2,1.])
        for rho in (-.8,0.,.75):
            p=rectangle_prob(a,b,rho)
            self.assertAlmostEqual(p.sum(),1.,places=10)
            self.assertTrue(np.all(p>0))
            expected=multivariate_normal.cdf([a[0],b[0]],mean=[0,0],cov=[[1,rho],[rho,1]])
            self.assertAlmostEqual(p[0,0],expected,places=7)
    def test_pair_recovery_and_symmetry(self):
        rng=np.random.default_rng(42)
        z=rng.multivariate_normal([0,0],[[1,.6],[.6,1]],size=5000)
        x=np.digitize(z,[-.8,-.2,.3,.9])
        self.assertAlmostEqual(polychoric_pair(x[:,0],x[:,1]),.6,delta=.04)
        self.assertAlmostEqual(polychoric_pair(x[:,0],x[:,1]),polychoric_pair(x[:,1],x[:,0]),places=6)
    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            polychoric_matrix(np.zeros((40,3)))
        with self.assertRaises(ArithmeticError):
            minres_promax(np.array([[1,.9,.9],[.9,1,-.9],[.9,-.9,1]]),1)
    def test_exact_factor_covariance(self):
        a=np.repeat(np.eye(3),3,axis=0)*.7
        phi=np.full((3,3),.35); np.fill_diagonal(phi,1)
        r=a@phi@a.T+np.eye(9)*.51
        fit=minres_promax(r,3)
        avg,accuracy=recover(fit.pattern,3,3)
        self.assertAlmostEqual(avg,.7,delta=.03)
        self.assertEqual(accuracy,1.)
        self.assertTrue(np.allclose(np.diag(fit.factor_correlation),1))
        self.assertLess(fit.rms_residual,.005)
    def test_parallel_reproducibility(self):
        x=simulate(600,2,3,.8,.2,False,0.,np.random.default_rng(17))
        a=parallel_analysis(x,10,5); b=parallel_analysis(x,10,5)
        np.testing.assert_array_equal(a.reference,b.reference)
        self.assertEqual(a.retained,2)
    def test_synthetic_accounting(self):
        out=run(n=400,k=2,items=3,reps=2)
        self.assertEqual(len(out["records"]),2)
        self.assertLessEqual(out["proper_fits"]+out["failed_fits"],2)

if __name__=="__main__":
    unittest.main()
