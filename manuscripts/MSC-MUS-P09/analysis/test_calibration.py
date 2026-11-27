import unittest
import numpy as np
from calibration import generate, run, cell, summarize, PROFILES, MECHANISMS


class CalibrationTests(unittest.TestCase):
    def test_bounded_integer_items_and_balanced_assignment(self):
        for profile in PROFILES:
            d = generate(np.random.default_rng(42), 588, profile, "complete", "alternative")
            self.assertEqual(d.music.value_counts().to_dict(), {0: 294, 1: 294})
            for col in ("understanding0", "understanding1", "understanding2", "distance0", "distance1"):
                values = d[col].to_numpy()
                self.assertTrue(np.all((values >= 0) & (values <= 10)))
                factor = 1 if col.startswith("distance") else 3
                np.testing.assert_allclose(values * factor, np.round(values * factor))

    def test_known_marginal_effects(self):
        d = generate(np.random.default_rng(21), 60000, "ceiling", "complete", "alternative")
        means = d.groupby("music")[["understanding2", "understanding1", "distance1"]].mean()
        np.testing.assert_allclose(means.loc[1]-means.loc[0], [.5, .5, 0], atol=.06)

    def test_missingness_and_shared_t1(self):
        for mechanism in MECHANISMS:
            d = generate(np.random.default_rng(23), 10000, "standard", mechanism, "null")
            np.testing.assert_array_equal(d.understanding1.isna(), d.distance1.isna())
            missing = d.understanding2.isna().mean()
            if mechanism == "complete":
                self.assertEqual(missing, 0.)
            else:
                self.assertGreater(missing, .1)
                self.assertLess(missing, .6)

    def test_reproducibility_and_denominators(self):
        result = run(5, 3, smoke=True)
        self.assertEqual(result, run(5, 3, smoke=True))
        self.assertEqual(len(result["cells"]), 4)
        for row in result["cells"]:
            for h in row["hypotheses"].values():
                self.assertEqual(h["fitted"]+h["failures"], 3)
                self.assertEqual(h["coverage"]["denominator"], h["fitted"])
                self.assertEqual(h["operational_rejection"]["denominator"], 3)

    def test_failure_is_not_coverage(self):
        result = summarize([], 0., 10)
        self.assertEqual(result["failures"], 10)
        self.assertIsNone(result["coverage"]["rate"])
        self.assertEqual(result["operational_rejection"]["rate"], 0.)


if __name__ == "__main__":
    unittest.main()
