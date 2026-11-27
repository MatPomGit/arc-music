import unittest
import numpy as np
from retest_calibration import distribution, population_agreement, simulate, wilson


class RetestCalibrationTests(unittest.TestCase):
    def test_exact_target(self):
        joint, follow = distribution("stable")
        self.assertAlmostEqual(joint.sum(), 1.)
        self.assertAlmostEqual(population_agreement(joint), .7)
        self.assertAlmostEqual(population_agreement(joint*follow[:, None]), .7)
        self.assertAlmostEqual(population_agreement(np.eye(5)), 1.)
        with self.assertRaises(ValueError):
            population_agreement(np.zeros((5, 5)))

    def test_shift_and_selection_change_target(self):
        joint, _ = distribution("shift")
        self.assertLess(population_agreement(joint), .7)
        joint, follow = distribution("selective")
        self.assertNotAlmostEqual(population_agreement(joint),
                                  population_agreement(joint*follow[:, None]))

    def test_failure_accounting(self):
        out = simulate(2, "stable", 3, 20, 7)
        self.assertEqual(out["intervals_available"], 0)
        self.assertEqual(out["operational_coverage"], 0.)
        self.assertIsNone(out["conditional_coverage"])
        self.assertIsNone(wilson(0, 0))

    def test_reproducibility_and_denominators(self):
        out = simulate(60, "stable", 3, 20, 7)
        self.assertEqual(out, simulate(60, "stable", 3, 20, 7))
        self.assertLessEqual(out["covered"], out["intervals_available"])
        self.assertLessEqual(out["intervals_available"], out["point_available"])
        self.assertLessEqual(out["point_available"], out["requested"])
        self.assertEqual(out["operational_coverage"], out["covered"]/out["requested"])
