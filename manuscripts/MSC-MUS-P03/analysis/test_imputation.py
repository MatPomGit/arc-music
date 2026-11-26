import unittest
import numpy as np
from models import prepare, fit
from imputation import draw_imputations, sensitivity, pool, shift_outcome
from test_analysis import fixture


class ImputationTests(unittest.TestCase):
    def test_observed_values_and_donor_bounds(self):
        raw = fixture(160)
        raw.loc[:14,"clarity_post"] = np.nan
        raw.loc[15:22,"source"] = None
        raw.loc[23:31,"motive_expression"] = np.nan
        data,_ = prepare(raw)
        draws = list(draw_imputations(data,m=3,sweeps=3,seed=8))
        for complete, mask in draws:
            self.assertEqual(int(mask.sum()),15)
            self.assertFalse(complete.isna().any().any())
            for key in ["clarity_post","source","motive_expression"]:
                observed = data[key].notna()
                np.testing.assert_array_equal(complete.loc[observed,key],data.loc[observed,key])
                self.assertTrue(set(complete[key]).issubset(set(data[key].dropna())))
            self.assertEqual(fit(complete,"H1")["n"],160)

    def test_no_missing_delta_invariance(self):
        result = sensitivity(fixture(100),m=3,sweeps=2,seed=9)
        self.assertEqual(result["missing_clarity_n"],0)
        values = [s["beta"] for s in result["scenarios"]]
        self.assertEqual(len(set(values)),1)

    def test_mnar_reproducibility_and_shared_draws(self):
        raw = fixture(150)
        raw.loc[raw.motive_expression > 8,"clarity_post"] = np.nan
        a = sensitivity(raw,m=3,sweeps=2,seed=5)
        self.assertEqual(a,sensitivity(raw,m=3,sweeps=2,seed=5))
        self.assertEqual([x["delta"] for x in a["scenarios"]],[-2,-1,0,1,2])
        self.assertLess(a["scenarios"][0]["beta"],a["scenarios"][-1]["beta"])
        for x in a["scenarios"]:
            self.assertLess(x["ci95"][0],x["beta"])
            self.assertGreater(x["ci95"][1],x["beta"])

    def test_differential_shift_integrity(self):
        raw = fixture(100)
        raw.loc[:2,"motive_expression"] = [0,5,10]
        raw.loc[:2,"clarity_post"] = [5,5,5]
        data,_ = prepare(raw)
        mask = np.zeros(len(data),dtype=bool)
        mask[:3] = True
        shifted = shift_outcome(data,mask,0,2)
        np.testing.assert_array_equal(shifted.clarity_post.iloc[:3],[3,5,7])
        np.testing.assert_array_equal(shifted.clarity_post.iloc[3:],data.clarity_post.iloc[3:])
        self.assertEqual(len(sensitivity(raw,m=2,sweeps=1)["differential_scenarios"]),12)

    def test_rubin_pool(self):
        a = pool([{"beta":.1,"se_hc3":.1,"n":100},
                  {"beta":.3,"se_hc3":.1,"n":100}])
        self.assertAlmostEqual(a["beta"],.2)
        self.assertAlmostEqual(a["se"]**2,.04)
        self.assertGreater(a["df"],0)

    def test_all_missing_core_fails(self):
        raw = fixture(100)
        raw["clarity_post"] = np.nan
        data,_ = prepare(raw)
        with self.assertRaises(ValueError):
            list(draw_imputations(data,m=2,sweeps=1))


if __name__ == "__main__":
    unittest.main()
