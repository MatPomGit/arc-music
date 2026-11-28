import unittest
import numpy as np
from python_structure_models import higher_moments, development_test


class PythonStructureTests(unittest.TestCase):
    def test_higher_order_recovers_exact_moments(self):
        d = np.repeat(np.arange(3), 4)
        l = np.linspace(.48, .72, len(d))
        g = np.array([.50, .60, .75])
        phi = np.outer(g, g) + np.diag(1-g*g)
        i, j = np.tril_indices(len(d), -1)
        corr = l[i]*l[j]*phi[d[i], d[j]]
        predicted, J, u, e, proper = higher_moments(corr, np.ones(len(corr)), d)
        self.assertTrue(proper)
        self.assertGreater(u, .01)
        self.assertGreater(e, .01)
        self.assertEqual(J.shape, (len(corr), len(d)+len(g)))
        np.testing.assert_allclose(predicted, corr, atol=1e-7)

    def test_development_test_is_not_scaled_wlsmv(self):
        rng = np.random.default_rng(42)
        J = rng.normal(size=(8, 3))
        influence = rng.normal(size=(200, 8))
        influence -= influence.mean(axis=0)
        out = development_test(np.zeros(8), np.zeros(8), J, influence)
        self.assertEqual(out["nominal_df"], 5)
        self.assertAlmostEqual(out["p_development"], 1.)
        self.assertNotIn("p_scaled", out)
