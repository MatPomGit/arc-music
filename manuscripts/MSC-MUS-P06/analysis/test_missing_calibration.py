import unittest
import numpy as np
from missing_calibration import slope,probability,run
from sensitivity import weighted_within,observation_probability
from simulation import draw
class TestMissingCalibration(unittest.TestCase):
    def test_weight_equivalence(self):
        g,x,y=draw(np.random.default_rng(23),80,6,.15,missing=0)
        w=np.random.default_rng(24).uniform(1,3,len(y))
        np.testing.assert_allclose(slope(g,x,y,w),weighted_within(g,x,y,w),atol=1e-10)
    def test_probability_equivalence(self):
        g,x,y=draw(np.random.default_rng(23),80,6,.15,missing=0)
        obs=np.random.default_rng(24).random(len(y))>.3
        np.testing.assert_allclose(probability(x,obs),observation_probability(x,obs),atol=1e-10)
    def test_reproducibility(self):
        a=run(seed=4,reps=2,n=80)
        b=run(seed=4,reps=2,n=80)
        self.assertEqual(a,b)
        self.assertEqual(len(a["cells"]),12)
        self.assertTrue(all(c["valid"]+c["failures"]==2 for c in a["cells"]))
if __name__=="__main__":unittest.main()
