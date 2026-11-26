import unittest
import numpy as np
from scipy.stats import t
from longitudinal_checks import design, fit
from mixed_checks import blocks, profile
from calibration_checks import cluster_gls, h10_estimates, screen


class CalibrationChecks(unittest.TestCase):
    def test_independent_covariance_oracle(self):
        x,y,g,c,m,_,_=design(np.random.default_rng(42),'h6',80,8,-.25,'mar')
        # Zero random-effect design and phi=0, unit residual SD: GLS=OLS.
        data=[(xx,yy,np.zeros_like(z),v,dist) for xx,yy,z,v,dist in
              blocks(x,y,m,80,8,'h6')]
        theta=np.zeros(6)
        _,beta,_=profile(theta,data,True)
        est,rad=cluster_gls(data,theta,beta,c)
        a,b,_=fit(x[m],y[m],g[m],c)
        groups=len(np.unique(g[m]))
        self.assertAlmostEqual(est,a,places=10)
        self.assertAlmostEqual(rad,b*t.ppf(.975,groups-x.shape[1])/
                               t.ppf(.975,groups-1),places=10)

    def test_h10_complete_data_estimators_agree(self):
        x,y,g,c,m,_,_=design(np.random.default_rng(42),'h10',80,8,-.35,'none')
        a,b=h10_estimates(x,y,g,c,m,80,8)
        np.testing.assert_allclose(a,b)

    def test_hidden_outcomes_invariant(self):
        x,y,g,c,m,_,_=design(np.random.default_rng(42),'h10',80,8,-.35,'mar')
        a=h10_estimates(x,np.where(m,y,np.nan),g,c,m,80,8)
        b=h10_estimates(x,np.where(m,y,1e9),g,c,m,80,8)
        np.testing.assert_array_equal(a,b)

    def test_screen_contract(self):
        a=screen('h10','mar',-.35,80,reps=8)
        self.assertEqual(a['paired_valid'],8)
        self.assertEqual(a['methods']['estimated_ipw']['requested'],8)
        self.assertTrue(0<=a['mean_last_observed_fraction']<=1)
        with self.assertRaises(ValueError):
            screen('h10','mar',-.35,41,reps=8)


if __name__=='__main__':
    unittest.main()
