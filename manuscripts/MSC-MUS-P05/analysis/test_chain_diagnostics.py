import unittest
import numpy as np
from chain_diagnostics import diagnose

class ChainTests(unittest.TestCase):
    def test_independent(self):
        x=np.random.default_rng(42).normal(size=(8,500))
        out=diagnose(x)
        self.assertEqual(out["status"],"screen_pass")
        self.assertLess(out["rhat"],1.01)
        self.assertGreater(out["bulk_ess"],400)
    def test_shift(self):
        x=np.random.default_rng(42).normal(size=(8,500))
        x[:4]+=3
        self.assertGreater(diagnose(x)["rhat"],1.1)
    def test_autocorrelation(self):
        rng=np.random.default_rng(42)
        x=np.zeros((8,500))
        for t in range(1,500):
            x[:,t]=.98*x[:,t-1]+rng.normal(size=8)
        self.assertLess(diagnose(x)["bulk_ess"],400)
    def test_unavailable(self):
        self.assertEqual(diagnose(np.ones((4,40)))["status"],"constant_trace")
        self.assertEqual(diagnose(np.ones((3,40)))["status"],"insufficient_or_invalid_trace")

if __name__=="__main__":
    unittest.main()
