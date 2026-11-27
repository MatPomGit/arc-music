import unittest
import numpy as np
from retest_ordinal_calibration import design, occasion_moments, target, simulate, draw_items


class OrdinalRetestCalibrationTests(unittest.TestCase):
    def test_probabilities_and_mcar_retention(self):
        joint, p, missing, follow = design("mcar")
        np.testing.assert_allclose(p.sum(axis=-1), 1)
        mass, _, _ = occasion_moments(p[0], missing[0])
        q = .8**5 + 5*.2*.8**4
        np.testing.assert_allclose(mass, q)
        self.assertAlmostEqual(target(joint, p, missing, follow)[1], .8*q*q)

    def test_exact_target_against_independent_sampling(self):
        joint, p, missing, follow = design("selective")
        truth, retention = target(joint, p, missing, follow)
        rng = np.random.default_rng(42)
        d = rng.choice(25, 80000, p=joint.ravel())
        x, y = d//5, d%5
        a = draw_items(rng, x, p[0], missing[0])
        b = draw_items(rng, y, p[1], missing[1])
        keep = (np.isfinite(a).sum(1)>=4) & (np.isfinite(b).sum(1)>=4)
        keep &= rng.random(len(d)) < follow[x]
        u, v = np.nanmean(a[keep], 1), np.nanmean(b[keep], 1)
        observed = 2*np.mean((u-u.mean())*(v-v.mean()))/(u.var()+v.var()+(u.mean()-v.mean())**2)
        self.assertAlmostEqual(keep.mean(), retention, delta=.01)
        self.assertAlmostEqual(observed, truth, delta=.025)

    def test_shift_and_selection(self):
        stable = target(*design("stable"))[0]
        self.assertLess(target(*design("shift"))[0], stable)
        j, p, m, f = design("selective")
        self.assertNotAlmostEqual(target(j, p, m, f)[0],
                                  target(j, p, np.zeros_like(m), np.ones(5))[0])

    def test_reproducibility_and_accounting(self):
        out = simulate(100, "mcar", 3, 20, 7)
        self.assertEqual(out, simulate(100, "mcar", 3, 20, 7))
        self.assertLessEqual(out["covered"], out["intervals_available"])
        self.assertLessEqual(out["intervals_available"], out["point_available"])
        self.assertLessEqual(out["point_available"], out["requested"])
        self.assertEqual(out["operational_coverage"], out["covered"]/out["requested"])
