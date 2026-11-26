"""Deterministic regression checks on estimands, missingness and simulations."""
import unittest
import numpy as np
from longitudinal_checks import design, fit, longitudinal, expertise

class LongitudinalChecks(unittest.TestCase):
    def test_complete_data(self):
        for kind in ('h6','h10'):
            x,y,g,c,m,pm,pt=design(np.random.default_rng(42),kind,120,8,-.25,'none')
            self.assertTrue(m.all())
            np.testing.assert_array_equal(pm,np.ones_like(pm))
            np.testing.assert_array_equal(pt,np.ones_like(pt))
            self.assertAlmostEqual(fit(x,y,g,c)[0],fit(x,y,g,c,pm)[0])
    def test_missingness(self):
        for kind in ('h6','h10'):
            for mode in ('mar','mnar'):
                x,y,g,c,m,pm,pt=design(np.random.default_rng(43),kind,120,8,-.25,mode)
                self.assertGreater(m.mean(),.4)
                self.assertLess(m.mean(),1.)
                self.assertTrue(np.all((pt>0)&(pt<=1)))
                self.assertEqual(np.array_equal(pm,pt),mode=='mar')
                if kind=='h10':
                    self.assertTrue(np.all(np.diff(m.reshape(120,8).astype(int),axis=1)<=0))
    def test_h10_endpoint_contrast(self):
        x,y,g,c,m,pm,pt=design(np.random.default_rng(44),'h10',120,8,-.35,'none')
        a=x.reshape(120,8,-1)
        np.testing.assert_allclose((a[1,-1]-a[1,0])-(a[0,-1]-a[0,0]),c)
    def test_cluster_and_mnar_diagnostics(self):
        for kind in ('h6','h10'):
            out=longitudinal(kind,reps=20,missing='mnar',seed=45)
            self.assertGreaterEqual(out['methods']['complete']['valid'],19)
            self.assertNotEqual(out['shift_means']['-0.5'],out['shift_means']['0.5'])
            for result in out['methods'].values():
                self.assertTrue(0<=result['coverage']<=1)
        out=expertise(reps=100,effect=0.,seed=46)
        self.assertLess(abs(out['rejection']-.05),.10)
    def test_invalid(self):
        with self.assertRaises(ValueError):
            longitudinal('h6',n=10)
        with self.assertRaises(ValueError):
            expertise(n=21)

if __name__=='__main__': unittest.main()
