import unittest
import numpy as np
from item_diagnostics import diagnose
from recovery import simulate

class ItemTests(unittest.TestCase):
    def test_sparse_missing_flags(self):
        x=simulate(200,2,3,.65,.3,False,0.,np.random.default_rng(42))
        x[:30,0]=np.nan; x[30:,0]=0
        out=diagnose(x,np.repeat(np.arange(2),3),list("abcdef"))
        self.assertIn("sparse_category",out["items"][0]["flags"])
        self.assertIn("extreme_endorsement",out["items"][0]["flags"])
        self.assertIn("missingness",out["items"][0]["flags"])
        self.assertIsNone(out["items"][0]["item_rest_spearman"])
        self.assertEqual(out["complete_n"],170)
    def test_local_residual(self):
        x=simulate(1000,2,3,.65,.3,False,0.,np.random.default_rng(42))
        out=diagnose(x,np.repeat(np.arange(2),3),list("abcdef"),np.full(6,.2),np.eye(2))
        self.assertTrue(out["local_dependence_available"])
        self.assertTrue(len(out["local_dependence_flags"])>=6)
    def test_invalid(self):
        x=np.ones((40,6))
        with self.assertRaises(ValueError):
            diagnose(x,np.repeat(np.arange(2),3),["same"]*6)
        with self.assertRaises(ValueError):
            diagnose(x,np.repeat(np.arange(2),3),list("abcdef"),np.ones(6),np.eye(2))

if __name__=="__main__":
    unittest.main()
