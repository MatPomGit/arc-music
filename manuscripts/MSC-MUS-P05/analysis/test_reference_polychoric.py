"""Independent numerical formulation: integrate conditional normal density."""
import unittest
import numpy as np
from scipy.integrate import quad
from scipy.special import ndtr
from scipy.stats import norm
from scipy.optimize import minimize_scalar
from ordinal_efa import rectangle_prob,polychoric_pair,thresholds

def reference_rectangles(a,b,rho):
    a=np.r_[-np.inf,a,np.inf]; b=np.r_[-np.inf,b,np.inf]
    sd=np.sqrt(1-rho*rho)
    out=np.empty((5,5))
    for i in range(5):
        for j in range(5):
            def density(z):
                return norm.pdf(z)*(ndtr((b[j+1]-rho*z)/sd)-ndtr((b[j]-rho*z)/sd))
            out[i,j]=quad(density,a[i],a[i+1],epsabs=1e-11,epsrel=1e-9)[0]
    return out

class NumericalReference(unittest.TestCase):
    def test_cells(self):
        for a,b in [(np.array([-.85,-.25,.25,.85]),np.array([-.9,-.3,.2,1.])),
                    (np.array([-.1,.3,.8,1.5]),np.array([-1.8,-1.,-.3,.2]))]:
            for rho in (-.85,-.3,0.,.6,.9):
                np.testing.assert_allclose(rectangle_prob(a,b,rho),reference_rectangles(a,b,rho),
                                           atol=2e-8,rtol=2e-6)
    def test_pair_optimizer(self):
        rng=np.random.default_rng(20261126)
        y=np.digitize(rng.multivariate_normal([0,0],[[1,.55],[.55,1]],size=800),
                     [-.85,-.25,.25,.85])
        a,b=y.T; ta,tb=thresholds(a),thresholds(b)
        count=np.bincount(a*5+b,minlength=25).reshape(5,5)
        def loss(r):
            return -np.sum(count*np.log(np.maximum(reference_rectangles(ta,tb,r),1e-15)))
        ref=minimize_scalar(loss,bounds=(-.98,.98),method="bounded",options={"xatol":1e-6})
        self.assertTrue(ref.success)
        self.assertAlmostEqual(polychoric_pair(a,b),ref.x,delta=2e-5)

if __name__=="__main__":
    unittest.main()
