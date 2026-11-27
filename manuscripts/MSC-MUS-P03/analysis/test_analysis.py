import unittest
import numpy as np
import pandas as pd
import statsmodels.api as sm
from models import analyze, prepare, fit, design, MOTIVES, OPS
from power import covariates, calibration, trial, simulate, wilson


def fixture(n=500, seed=7):
    rng = np.random.default_rng(seed)
    x = covariates(rng, n, .2)
    raw = pd.DataFrame(x[:, 1:5], columns=MOTIVES)
    raw["clarity_pre"] = x[:, 5]
    raw["age"], raw["experience"], raw["use_days"], raw["recency"] = x[:, 6], x[:, 7], x[:, 8], x[:, 9]
    raw["source"] = np.where(x[:, 10], "community", np.where(x[:, 11], "other", "university"))
    raw["clarity_post"] = 5+.25*(x[:,5]-5)+.2*(x[:,1]-5)+rng.uniform(-1,1,n)
    raw["valence_pre"] = rng.uniform(0,10,n)
    raw["valence_post"] = 5+.3*(raw.valence_pre-5)+.2*(raw.motive_mood-5)+rng.uniform(-1,1,n)
    for k in OPS:
        raw[k] = (rng.uniform(size=n)<raw.motive_explore/10).astype(float)
    raw["agency"] = rng.uniform(0,10,n)
    raw["resonance"] = 5+.4*(raw.agency-5)+rng.uniform(-1,1,n)
    raw["consent"] = raw["eligible"] = True
    raw["study_id"] = [f"p03-00000000-0000-4000-8000-{i:012x}" for i in range(n)]
    return raw


class ModelTests(unittest.TestCase):
    def test_four_models_and_holm(self):
        result = analyze(fixture())
        for h, row in result["models"].items():
            self.assertEqual(row["n"], 500)
            self.assertGreater(row["beta"], 0)
            self.assertLess(row["p"], .05)
            if h != "H1":
                self.assertGreaterEqual(row["p_holm"], row["p"]-1e-12)

    def test_missing_operations_are_not_zero(self):
        raw = fixture()
        raw.loc[0, "regenerated"] = np.nan
        raw.loc[1, OPS] = 0
        data, _ = prepare(raw)
        self.assertTrue(np.isnan(data.loc[0, "iteration_count"]))
        self.assertEqual(data.loc[1, "iteration_count"], 0)
        self.assertEqual(fit(data,"H3")["n"], 499)
        self.assertTrue(data["operation_diversity"].equals(data["iteration_count"]))
        self.assertEqual(data.loc[1,"operation_diversity"],0)

    def test_filter_and_range(self):
        raw = fixture()
        raw.loc[0,"eligible"] = False
        raw.loc[1,"consent"] = False
        raw.loc[2,"clarity_post"] = 11
        raw.loc[3,"source"] = "invalid"
        raw.loc[4,"edited"] = .5
        data, invalid = prepare(raw)
        self.assertEqual(len(data),498)
        self.assertEqual(invalid["clarity_post"],1)
        self.assertEqual(invalid["source"],1)
        self.assertEqual(invalid["edited"],1)
        self.assertEqual(fit(data,"H1")["n"],496)

    def test_duplicate_rejected(self):
        raw = fixture()
        raw.loc[1,"study_id"] = raw.loc[0,"study_id"]
        with self.assertRaises(ValueError):
            prepare(raw)

    def test_hc3_matches_statsmodels(self):
        data, _ = prepare(fixture())
        y,x,k = design(data,"H1")
        expected = sm.OLS(y,x).fit(cov_type="HC3",use_t=True)
        actual = fit(data,"H1")
        self.assertAlmostEqual(actual["beta"],expected.params[k],places=12)
        self.assertAlmostEqual(actual["se_hc3"],expected.bse[k],places=12)
        self.assertTrue(-1 <= actual["partial_r"] <= 1)

    def test_rank_failure_explicit(self):
        raw=fixture()
        raw["source"]="university"
        self.assertIn("error",analyze(raw)["models"]["H1"])


class PowerTests(unittest.TestCase):
    def test_calibration(self):
        self.assertEqual(calibration(.2,0),0)
        self.assertGreater(calibration(.6,.15),calibration(.2,.15))

    def test_trial_and_wilson(self):
        n,beta,rejected,covered=trial(np.random.default_rng(42),.2,.06,False)
        self.assertEqual(n,480)
        self.assertTrue(np.isfinite(beta))
        lo,hi=wilson(90,100)
        self.assertLess(lo,.9)
        self.assertGreater(hi,.9)

    def test_reproducibility(self):
        a=simulate(3,10)
        self.assertEqual(a,simulate(3,10))
        self.assertEqual(len(a["scenarios"]),8)
        self.assertEqual(a["data_kind"],"synthetic")


if __name__ == "__main__":
    unittest.main()
