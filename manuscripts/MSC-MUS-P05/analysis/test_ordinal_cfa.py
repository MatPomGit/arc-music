import unittest
import numpy as np
from ordinal_cfa import fit_moments,fit_cfa
from ordinal_reliability import omega_latent_response,omega_observed_sum
from recovery import simulate

class CFA(unittest.TestCase):
    def test_exact_moments(self):
        d=np.repeat(np.arange(3),4)
        l=np.linspace(.52,.8,len(d))
        phi=np.full((3,3),.35); np.fill_diagonal(phi,1)
        i,j=np.tril_indices(len(d),-1)
        cuts=np.tile([-.8,-.2,.3,.9],(len(d),1))
        fit=fit_moments(l[i]*l[j]*phi[d[i],d[j]],np.ones(len(i)),cuts,d)
        self.assertTrue(fit.proper)
        np.testing.assert_allclose(fit.loadings,l,atol=1e-5)
        np.testing.assert_allclose(fit.phi,phi,atol=1e-5)
    def test_synthetic(self):
        x=simulate(1500,2,4,.65,.3,False,0.,np.random.default_rng(42))
        fit=fit_cfa(x,np.repeat(np.arange(2),4))
        self.assertTrue(fit.proper)
        self.assertLess(np.max(np.abs(fit.loadings-.65)),.12)
        self.assertAlmostEqual(fit.phi[0,1],.3,delta=.12)
    def test_invalid_assignment(self):
        with self.assertRaises(ValueError):
            fit_moments([],[],[],[0,0,1,1])
    def test_omega(self):
        l=np.full(5,.7); cuts=np.tile([-.8,-.2,.3,.9],(5,1))
        self.assertAlmostEqual(omega_latent_response(l),5*.49/(1+4*.49))
        score=omega_observed_sum(l,cuts)
        self.assertGreater(score,.65)
        self.assertLess(score,omega_latent_response(l))
        self.assertAlmostEqual(omega_observed_sum(np.zeros(5),cuts),0.,places=10)
    def test_bad_thresholds(self):
        with self.assertRaises(ValueError):
            omega_observed_sum([.5,.5,.5],np.zeros((3,4)))

if __name__=="__main__":
    unittest.main()
