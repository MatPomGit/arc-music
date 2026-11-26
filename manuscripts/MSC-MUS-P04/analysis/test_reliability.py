import unittest
import numpy as np
from reliability import conditional_moments,omega_from_moments,fit_ordinal,reliability
from measurement_calibration import items_from_latent,population_reference,generate,scenario

class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(42)
        self.items=items_from_latent(rng.normal(size=700),.9,rng)
    def test_moments(self):
        t=np.tile([-1.5,-.9,-.35,.2,.8,1.4],(6,1))
        m,v=conditional_moments(t,np.full(6,.6),np.array([-2.,0.,2.]))
        self.assertTrue(np.all(np.diff(m,axis=0)>0))
        self.assertTrue(np.all(v>=0))
        omega,truth,error=omega_from_moments(m,v,np.array([.25,.5,.25]))
        self.assertAlmostEqual(omega,truth/(truth+error))
    def test_fit(self):
        fit=fit_ordinal(self.items)
        self.assertTrue(0<fit["omega_categorical"]<1)
        self.assertLess(fit["rms_off_diagonal_correlation_residual"],.1)
        self.assertEqual(fit["n_complete"],700)
    def test_bootstrap(self):
        x=self.items.astype(float); x[0,0]=np.nan
        out=reliability(x,reps=8,seed=3)
        self.assertEqual(out["n_incomplete"],1)
        self.assertEqual(out["bootstrap_valid"]+sum(out["bootstrap_failures"].values()),8)
        self.assertEqual(out,reliability(x,reps=8,seed=3))
    def test_guards(self):
        for x in (self.items[:20],np.ones((150,6)),np.ones((150,24))):
            with self.assertRaises(ValueError): fit_ordinal(x)
    def test_noise_effect(self):
        a=population_reference(.5,1,n=12000); b=population_reference(1.4,1,n=12000)
        self.assertGreater(a["latent_score_correlation"],b["latent_score_correlation"])
    def test_calibration(self):
        ref=population_reference(.9,5,n=12000)
        out=scenario(300,.6,.9,ref,5,8)
        self.assertAlmostEqual(out["methods"]["observed"]["target"],.6*ref["latent_score_correlation"])
        self.assertAlmostEqual(out["methods"]["oracle"]["target"],.6)
        for q in out["methods"].values():
            self.assertEqual(q["valid"],5)
            self.assertEqual(q["failed"],0)
