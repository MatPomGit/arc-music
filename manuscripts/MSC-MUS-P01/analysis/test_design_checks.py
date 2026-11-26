import math
import unittest
from design_checks import welch_sim, pooled_oracle, diary_sim, interaction_sim, novelty_sim

class DesignChecks(unittest.TestCase):
    def test_oracle(self):
        self.assertAlmostEqual(pooled_oracle(175,.3),pooled_oracle(175,-.3),places=12)
        self.assertAlmostEqual(pooled_oracle(88,0,4,.1),.1,places=10)
        for n,k in [(176,2),(88,4)]:
            self.assertGreaterEqual(pooled_oracle(n,.3,k),.8)
            self.assertLess(pooled_oracle(n-1,.3,k),.8)
    def test_welch(self):
        for effect in (0.,.3):
            out=welch_sim([88]*4,[1]*4,effect,seed=1729)
            expected=pooled_oracle(88,effect,4)
            self.assertLess(abs(out['rejection']-expected),5*math.sqrt(expected*(1-expected)/out['valid'])+.003)
            self.assertLess(abs(out['coverage']-.95),5*math.sqrt(.95*.05/out['valid'])+.003)
        out=welch_sim([90,110,85,125],[.7,1.3,1.,1.5],0.,loss=.15)
        self.assertLess(abs(out['rejection']-.05),.012)
    def test_cluster_and_interactions(self):
        for fn in (diary_sim,interaction_sim,novelty_sim):
            out=fn(effect=0.,reps=500)
            self.assertLess(abs(out['rejection']-.05),.045)
            self.assertGreater(out['valid'],450)
    def test_invalid(self):
        for n,sd in (([5.5,5],[1,1]),([5,5],[1,0]),([1,5],[1,1])):
            with self.assertRaises(ValueError): welch_sim(n,sd,0.)

if __name__=='__main__': unittest.main()
