import unittest
import numpy as np
from scipy.stats import multivariate_normal
from longitudinal_checks import design
from mixed_checks import covariance,profile,blocks,mixed_fit,estimated_probability,bootstrap

class MixedChecks(unittest.TestCase):
    def sample(self,kind,mode):
        x,y,g,c,m,_,_=design(np.random.default_rng(42),kind,80,8,-.25,mode)
        return x,np.where(m,y,np.nan),c,m
    def test_covariance_and_likelihood(self):
        x,y,c,m=self.sample('h10','mar')
        b=blocks(x,y,m,80,8,'h10')
        theta=np.array([0.,.2,-1.,-.1,.5,.1])
        nll,beta,_=profile(theta,b,True)
        oracle=0.
        for xx,yy,z,v,d in b:
            cov=covariance(theta,z,v,d)
            for i in range(len(yy)):
                self.assertGreater(np.linalg.eigvalsh(cov[i]).min(),0.)
                oracle-=multivariate_normal.logpdf(yy[i],mean=xx[i]@beta,cov=cov[i])
        self.assertAlmostEqual(nll,oracle,places=7)
    def test_fits_and_mask(self):
        for kind in ('h6','h10'):
            x,y,c,m=self.sample(kind,'mar')
            v=mixed_fit(x,y,m,80,8,kind,c)
            self.assertTrue(np.isfinite(v['estimate']))
            self.assertGreater(v['radius'],0.)
            p=estimated_probability(x,y,m,80,8,kind)
            self.assertTrue(np.all((p>=.025)&(p<=1)))
            y2=y.copy();y2[~m]=1e8
            np.testing.assert_array_equal(p,estimated_probability(x,y2,m,80,8,kind))
            a=bootstrap(x,y,m,80,8,kind,c,reps=39)
            b=bootstrap(x,y2,m,80,8,kind,c,reps=39)
            self.assertEqual(a,b)
            self.assertNotEqual(a['estimate'][0],a['estimate'][2])
            self.assertEqual(a['valid'],39)
    def test_no_missingness(self):
        for kind in ('h6','h10'):
            x,y,c,m=self.sample(kind,'none')
            np.testing.assert_array_equal(estimated_probability(x,y,m,80,8,kind),np.ones(len(y)))
            a=bootstrap(x,y,m,80,8,kind,c,reps=39)
            np.testing.assert_allclose(a['estimate'],[a['estimate'][0]]*3)

if __name__=='__main__':unittest.main()
