import unittest
import numpy as np
from retest import icc_a1, retest_domain


def row(person, stage, lag=None):
    return dict(participant_code=person, episode_code="episode", stage=stage, lag_days=lag)


class RetestTests(unittest.TestCase):
    def test_exact_agreement_and_shift(self):
        x = np.arange(3.)
        self.assertAlmostEqual(icc_a1(np.column_stack([x, x])), 1.)
        self.assertAlmostEqual(icc_a1(np.column_stack([x, x+1])), 2/3)
        self.assertLess(icc_a1(np.column_stack([x, x[::-1]])), 0.)

    def test_degenerate(self):
        with self.assertRaises(ValueError):
            icc_a1(np.ones((4, 2)))

    def test_linkage_and_missing(self):
        rows = [row(f"s{i}", "cfa") for i in range(40)]
        rows += [row(f"s{i}", "retest", 10) for i in reversed(range(40))]
        x = np.repeat((np.arange(40) % 5)[:, None], 5, axis=1).astype(float)
        y = x[::-1].copy()
        y[0, :2] = np.nan
        out = retest_domain(rows, np.vstack([x, y]), authorized=True, reps=100)
        self.assertEqual(out["complete_pairs"], 39)
        self.assertEqual(out["incomplete_pairs"], 1)
        self.assertAlmostEqual(out["icc"], 1.)
        self.assertEqual(out["icc_interval"], [1., 1.])
        self.assertEqual(out["mean_difference"], 0.)

    def test_authorization_and_invalid_metadata(self):
        rows = [row("s1", "cfa"), row("s1", "retest", 6)]
        with self.assertRaises(ValueError):
            retest_domain(rows, np.zeros((2, 5)))
        with self.assertRaisesRegex(ValueError, "lag outside"):
            retest_domain(rows, np.zeros((2, 5)), authorized=True)

    def test_no_pairs_and_invalid_length(self):
        rows = [row("s1", "cfa")]
        self.assertEqual(retest_domain(rows, np.zeros((1, 5)), authorized=True)["status"], "unavailable")
        with self.assertRaisesRegex(ValueError, "row counts"):
            retest_domain(rows, np.zeros((2, 5)), authorized=True)

    def test_bootstrap_failure_retained(self):
        rows = [row("s1", "cfa"), row("s2", "cfa"), row("s1", "retest", 7), row("s2", "retest", 7)]
        x = np.repeat(np.array([0., 4., 0., 4.])[:, None], 5, axis=1)
        out = retest_domain(rows, x, authorized=True, min_pairs=2, reps=100)
        self.assertEqual(out["status"], "interval_unavailable")
        self.assertGreater(out["bootstrap_failed"], 5)
        self.assertNotIn("icc_interval", out)
