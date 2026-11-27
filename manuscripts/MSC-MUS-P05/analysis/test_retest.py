import unittest
import numpy as np
from retest import icc_a1, retest_domain


def row(person, stage, lag=None):
    return dict(participant_code=person, episode_code="episode", stage=stage, lag_days=lag)


def records(rows, items):
    return [((r["participant_code"], r["stage"], r["episode_code"]), x)
            for r, x in zip(rows, items)]


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
        out = retest_domain(rows, records(rows, np.vstack([x, y])), authorized=True, reps=100)
        self.assertEqual(out["complete_pairs"], 39)
        self.assertEqual(out["incomplete_pairs"], 1)
        self.assertAlmostEqual(out["icc"], 1.)
        self.assertEqual(out["icc_interval"], [1., 1.])
        self.assertEqual(out["mean_difference"], 0.)

    def test_authorization_and_invalid_metadata(self):
        rows = [row("s1", "cfa"), row("s1", "retest", 6)]
        with self.assertRaises(ValueError):
            retest_domain(rows, records(rows, np.zeros((2, 5))))
        out = retest_domain(rows, records(rows, np.zeros((2, 5))), authorized=True)
        self.assertEqual(out["excluded_retests"]["outside_window"], 1)

    def test_no_pairs_and_invalid_length(self):
        rows = [row("s1", "cfa")]
        self.assertEqual(retest_domain(rows, records(rows, np.zeros((1, 5))), authorized=True)["status"], "unavailable")
        with self.assertRaisesRegex(ValueError, "keys differ"):
            retest_domain(rows, [], authorized=True)

    def test_bootstrap_failure_retained(self):
        rows = [row("s1", "cfa"), row("s2", "cfa"), row("s1", "retest", 7), row("s2", "retest", 7)]
        x = np.repeat(np.array([0., 4., 0., 4.])[:, None], 5, axis=1)
        out = retest_domain(rows, records(rows, x), authorized=True, min_pairs=2, reps=100)
        self.assertEqual(out["status"], "interval_unavailable")
        self.assertGreater(out["bootstrap_failed"], 5)
        self.assertNotIn("icc_interval", out)

    def test_ineligible_retests_do_not_change_agreement(self):
        rows = [row(f"s{i}", "cfa") for i in range(40)]
        rows += [row(f"s{i}", "retest", 10) for i in range(36)]
        x = np.repeat((np.arange(40) % 5)[:, None], 5, axis=1)
        data = records(rows, np.vstack([x, x[:36]]))
        clean = retest_domain(rows, data, authorized=True, reps=100)
        bad = [row("s36", "retest", 6), row("s37", "retest", None),
               dict(row("s38", "retest", 10), episode_code="other"),
               row("orphan", "retest", 10)]
        out = retest_domain(rows+bad, data+records(bad, np.full((4, 5), 4)),
                            authorized=True, reps=100)
        self.assertEqual(out["excluded_retests"], dict(no_cfa_parent=1, episode_mismatch=1,
                                                       invalid_lag=1, outside_window=1))
        for key in ("icc", "icc_interval", "complete_pairs", "mean_difference"):
            self.assertEqual(clean[key], out[key])
        self.assertEqual(out["retest_records"], 40)

    def test_keyed_input_order_and_duplicates(self):
        rows = [row(f"s{i}", "cfa") for i in range(40)]
        rows += [row(f"s{i}", "retest", 10) for i in range(40)]
        x = np.repeat((np.arange(40) % 5)[:, None], 5, axis=1)
        data = records(rows, np.vstack([x, x]))
        expected = retest_domain(rows, data, authorized=True, reps=100)
        self.assertEqual(expected, retest_domain(rows[::-1], data[::-1], authorized=True, reps=100))
        with self.assertRaisesRegex(ValueError, "duplicate item"):
            retest_domain(rows, data+[data[0]], authorized=True)
        with self.assertRaisesRegex(ValueError, "keys differ"):
            retest_domain(rows, data[1:], authorized=True)
        with self.assertRaisesRegex(ValueError, "duplicate participant-stage"):
            retest_domain(rows+[row("s0", "retest", 15)], data, authorized=True)
