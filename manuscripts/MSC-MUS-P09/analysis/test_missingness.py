import unittest
import numpy as np
from calibration import generate
from inference import analyze, prepare
from missingness import points, sensitivity_endpoint, analyze_missingness
from test_inference import fixture


class MissingnessTests(unittest.TestCase):
    def test_complete_reduces_to_arm_mean_difference(self):
        d = prepare(fixture())
        expected = d.groupby("music").understanding2.mean().diff().iloc[-1]
        estimates, diag = points(d, "understanding2")
        self.assertEqual(len(estimates), 26)
        for value in estimates.values():
            self.assertAlmostEqual(value, expected)
        self.assertTrue(all(x["max_weight"] == 1 for x in diag))

    def test_mar_recovery_and_mnar_shift_ordering(self):
        d = generate(np.random.default_rng(42), 20000, "standard", "MAR", "alternative")
        est, _ = points(d, "understanding2")
        self.assertAlmostEqual(est["ipw"], .5, delta=.08)
        self.assertAlmostEqual(est["shift_0/0"], .5, delta=.08)
        self.assertLess(est["shift_2/-2"], est["shift_0/0"])
        self.assertGreater(est["shift_-2/2"], est["shift_0/0"])

    def test_reproducibility_and_intervals(self):
        d = fixture()
        d.loc[d.index % 5 == 0, "understanding21"] = np.nan
        first = analyze_missingness(d, reps=9, seed=123)
        self.assertEqual(first, analyze_missingness(d, reps=9, seed=123))
        h = first["hypotheses"]["H1"]["estimates"]
        self.assertEqual(len(h), 26)
        for row in h.values():
            self.assertEqual(row["successful"]+row["failed"], 9)
            self.assertIsNotNone(row["ci"])
            self.assertLessEqual(row["ci"][0], row["ci"][1])

    def test_undefined_blocks_numeric_full_cohort_analysis(self):
        for status in ("undefined", "unknown"):
            d = fixture()
            d.loc[0, "target_status2"] = status
            d.loc[0, ["understanding21", "understanding22", "understanding23"]] = np.nan
            r = analyze_missingness(d, reps=3)["hypotheses"]
            self.assertIn("unavailable", r["H1"])
            self.assertNotIn("estimates", r["H1"])
            self.assertIn("estimates", r["H2"])
            self.assertIn("unavailable", analyze(d)["missingness"]["H1"])
            self.assertEqual(analyze(d)["randomised"], 320)

    def test_undefined_secondary_is_not_a_confirmatory_test(self):
        d = fixture()
        d.loc[0,"target_status1"] = "undefined"
        d.loc[0,["understanding11","understanding12","understanding13","distance1"]] = np.nan
        result = analyze(d)
        for h in ("H2","H3"):
            self.assertFalse(result["hypotheses"][h]["confirmatory_available"])
            self.assertIn("descriptive_p",result["hypotheses"][h])
            self.assertNotIn("p",result["hypotheses"][h])
            self.assertIsNone(result["secondary_holm"][h])
        self.assertIn("p",result["hypotheses"]["H1"])

    def test_observed_score_conflicts_with_undefined(self):
        d = fixture()
        d.loc[0, "target_status2"] = "undefined"
        with self.assertRaises(ValueError):
            prepare(d)

    def test_wrong_event_is_not_structural_undefined(self):
        d = fixture()
        d.loc[0, "same_event2"] = False
        p = prepare(d)
        self.assertEqual(p.loc[0, "target_status2"], "defined")
        self.assertTrue(np.isnan(p.loc[0, "understanding2"]))
        self.assertIn("estimates", sensitivity_endpoint(p, "understanding2", "target_status2", 3))

    def test_no_observed_arm_fails_closed(self):
        d = fixture()
        d.loc[d.music == 1, "understanding21"] = np.nan
        p = prepare(d)
        r = sensitivity_endpoint(p, "understanding2", "target_status2", 3)
        self.assertIn("unavailable", r)
        self.assertNotIn("estimates", r)


if __name__ == "__main__":
    unittest.main()
