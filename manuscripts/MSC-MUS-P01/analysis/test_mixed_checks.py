import unittest
import numpy as np
from scipy.stats import multivariate_normal
from longitudinal_checks import design
from mixed_checks import covariance,profile,blocks,mixed_fit,estimated_probability,bootstrap,wilson,diagnostic_summary

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
    def test_total_dropout_and_invalid_history(self):
        x,y,c,m=self.sample('h10','none')
        m=m.reshape(80,8)
        m[:,1:]=False
        p=estimated_probability(x,np.where(m.ravel(),y,np.nan),m.ravel(),80,8,'h10').reshape(80,8)
        np.testing.assert_array_equal(p[:,0],np.ones(80))
        np.testing.assert_array_equal(p[:,1:],np.full((80,7),.025))
        m[0,2]=True
        with self.assertRaisesRegex(ValueError,'monotone'):
            estimated_probability(x,y,m.ravel(),80,8,'h10')
        m[0,2]=False
        m[0,0]=False
        with self.assertRaisesRegex(ValueError,'baseline'):
            estimated_probability(x,y,m.ravel(),80,8,'h10')
    def test_monte_carlo_precision(self):
        self.assertGreater(wilson(0,8)[1],.3)
        self.assertLess(wilson(8,8)[0],.7)
        self.assertGreater(wilson(0,8)[1],wilson(0,1000)[1])
        s=diagnostic_summary([(0.,1.)]*8,0.,10)
        self.assertEqual(s['failed'],2)
        self.assertEqual(s['valid_fraction'],.8)
        self.assertGreater(s['rejection_mc_interval'][1],.3)
        self.assertLess(s['coverage_mc_interval'][0],.7)
    def test_no_missingness(self):
        for kind in ('h6','h10'):
            x,y,c,m=self.sample(kind,'none')
            np.testing.assert_array_equal(estimated_probability(x,y,m,80,8,kind),np.ones(len(y)))
            a=bootstrap(x,y,m,80,8,kind,c,reps=39)
            np.testing.assert_allclose(a['estimate'],[a['estimate'][0]]*3)

if __name__=='__main__':unittest.main()
