import unittest

import numpy as np
from rounded_sensitivity_calibration import coverage, split_rhat, wilson, hearing_retention


class DiagnosticTests(unittest.TestCase):
    def test_hearing_retention(self):
        r=hearing_retention(720)
        self.assertAlmostEqual(r["expected_observed"],532.8)
        self.assertAlmostEqual(r["attainment"],.9973566511613955,places=10)
        self.assertAlmostEqual(hearing_retention(660)["attainment"],.16208532385605012,places=10)
        self.assertGreater(r["attainment"],hearing_retention(700)["attainment"])
        with self.assertRaises(ValueError):
            hearing_retention(721)
        with self.assertRaises(ValueError):
            hearing_retention(720,measurement_loss=-.1)

    def test_accounting(self):
        r=coverage([[-1,1],[.1,2]],3)
        self.assertEqual(r["coverage"],.5)
        self.assertEqual(r["operational_coverage"],1/3)
        self.assertEqual(r["failures"],1)
        self.assertIsNone(coverage([],2)["coverage"])
        with self.assertRaises(ValueError):
            coverage([[1,-1]],1)

    def test_rank_diagnostic(self):
        x=np.random.default_rng(42).normal(size=(4,1000))
        self.assertLess(split_rhat(x)["maximum"],1.05)
        x[0]+=5
        self.assertGreater(split_rhat(x)["maximum"],1.1)
        self.assertIsNone(split_rhat(np.ones((4,20)))["maximum"])
        with self.assertRaises(ValueError):
            split_rhat(np.ones((1,20)))

    def test_wilson(self):
        lo,hi=wilson(9,10)
        self.assertAlmostEqual(lo,.5958499732)
        self.assertAlmostEqual(hi,.9821237869)


if __name__=="__main__":
    unittest.main()
