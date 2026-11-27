import unittest
import numpy as np
from cp_joint_power import decision, run


class CentralPredictionTests(unittest.TestCase):
    def test_both_effects_required(self):
        m=np.array([[.4,0.,0.,.4],[.8,0.,0.,0.],[.9,0.,0.,-.1]])
        ok,success,s,rad,psi,pr=decision(m,np.ones_like(m),np.full_like(m,1000))
        self.assertTrue(ok.all())
        np.testing.assert_array_equal(success,[True,False,False])
        self.assertTrue((psi-pr>0).all())

    def test_unavailable_cell(self):
        m=np.array([[.4,0.,0.,.4]])
        ok,success,*_=decision(m,np.ones_like(m),np.array([[100,100,1,100]]))
        self.assertFalse(ok[0])
        self.assertFalse(success[0])

    def test_reproducibility_and_accounting(self):
        result=run(20,123)
        self.assertEqual(len(result),96)
        self.assertEqual(result,run(20,123))
        self.assertTrue(all(x["valid"]+x["failed"]==20 for x in result))
