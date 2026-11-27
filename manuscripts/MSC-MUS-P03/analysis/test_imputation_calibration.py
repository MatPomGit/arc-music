import unittest
from unittest.mock import patch

import numpy as np

from imputation_calibration import mask_and_stop, raw_records, run, summary, mixed_mar_attainment, estimates
from stress import generate
from imputation_calibration import oracle_estimates, paired_difference, missing_probabilities


class CalibrationTests(unittest.TestCase):
    def test_exact_mixed_mar_attainment(self):
        result = mixed_mar_attainment()
        self.assertAlmostEqual(result["p_complete"], .7946660954548412, places=12)
        self.assertAlmostEqual(result["caps"][0]["attainment"], .8135951928199157, places=10)
        self.assertAlmostEqual(result["caps"][1]["attainment"], .991001488006452, places=10)
        self.assertTrue(all(a["attainment"] < b["attainment"]
                            for a,b in zip(result["caps"],result["caps"][1:])))
        with self.assertRaises(ValueError):
            mixed_mar_attainment(500,(480,))

    def test_complete_stopping_rule(self):
        rng = np.random.default_rng(42)
        x, y = generate(rng, 120, .6, .08, True)
        data, n = mask_and_stop(rng, raw_records(x,y), "complete", 100)
        self.assertEqual(len(data), 100)
        self.assertEqual(n,100)
        self.assertFalse(data.clarity_post.isna().any())

    def test_missing_records_retained_until_target(self):
        rng = np.random.default_rng(42)
        x, y = generate(rng, 300, .6, .08, True)
        data, n = mask_and_stop(rng, raw_records(x,y), "mixed_mar", 150)
        self.assertEqual(n,150)
        self.assertGreater(len(data),n)
        self.assertTrue(data.clarity_post.isna().any())
        self.assertTrue(data.motive_expression.isna().any())

    def test_failure_accounting(self):
        a = summary([dict(beta=.1,ci95=[0,.2],p=.1),None],.1)
        self.assertEqual(a["coverage"],1.)
        self.assertEqual(a["operational_coverage"],.5)
        self.assertEqual(a["failures"],1)
        self.assertIsNone(summary([None,None],.1)["coverage"])

    def test_invalid_inference_is_counted_as_failure(self):
        valid = dict(beta=.1, ci95=[0,.2], p=.1)
        malformed = [
            dict(valid, beta=np.nan),
            dict(valid, p=np.inf),
            dict(valid, p=1.1),
            dict(valid, ci95=[.2,0]),
            dict(valid, ci95=[0,.05]),
            dict(valid, ci95=[0,np.inf]),
            dict(valid, ci95=[0]),
            dict(beta=.1, p=.1),
        ]
        result = summary([valid, *malformed, None], .1)
        self.assertEqual(result["fitted"], 1)
        self.assertEqual(result["failures"], 9)
        self.assertEqual(result["invalid_results"], 8)
        self.assertEqual(result["coverage"], 1.)
        self.assertEqual(result["operational_coverage"], .1)
        self.assertTrue(np.isfinite(result["bias"]))
        with self.assertRaises(ValueError):
            summary([valid], np.nan)

    def test_failed_shift_does_not_invalidate_other_scenarios(self):
        valid = dict(beta=.1, ci95=[0,.2], p=.1)
        def shifted(completed, missing, delta, slope):
            return slope
        def fitted(data, hypothesis):
            if data == -2:
                raise ValueError("synthetic scenario failure")
            return valid
        with patch("imputation_calibration.draw_imputations",
                   return_value=iter([(0, None), (0, None)])), \
             patch("imputation_calibration.shift_outcome", side_effect=shifted), \
             patch("imputation_calibration.fit", side_effect=fitted), \
             patch("imputation_calibration.pool", return_value=valid):
            result = estimates(0, m=2, sweeps=1, seed=42)
        self.assertEqual(result["complete_case"], valid)
        self.assertEqual(result["mi_zero"], valid)
        self.assertIsNone(result["mi_slope_minus2"])
        self.assertEqual(result["mi_slope_plus2"], valid)

    def test_small_reproducible_production_screen(self):
        kw = dict(reps=2,m=2,sweeps=1,target=100,cap=160,reference_n=1000)
        a = run("mixed_mar",**kw)
        self.assertEqual(a,run("mixed_mar",**kw))
        for c in a["cells"]:
            for v in c["methods"].values():
                self.assertEqual(v["fitted"]+v["failures"],2)
                self.assertEqual(v["fitted"],2)

    def test_oracle_complete_matches_observed_fit(self):
        rng=np.random.default_rng(42)
        x,y=generate(rng,160,.6,.08,True)
        raw=raw_records(x,y)
        data,_=mask_and_stop(rng,raw,"complete",100)
        result=oracle_estimates(raw,data,"complete")
        self.assertAlmostEqual(result["oracle_full"]["beta"],result["oracle_ipw"]["beta"],places=10)
        self.assertAlmostEqual(result["oracle_full"]["ci95"][0],result["oracle_ipw"]["ci95"][0],places=10)
        changed=data.copy()
        changed.loc[0,"study_id"]=data.loc[1,"study_id"]
        with self.assertRaises(ValueError):
            oracle_estimates(raw,changed,"complete")

    def test_oracle_paired_screen_does_not_change_production_draws(self):
        kw=dict(reps=2,m=2,sweeps=1,target=100,cap=160,reference_n=1000)
        baseline=run("mixed_mar",**kw)
        paired=run("mixed_mar",oracle_benchmark=True,**kw)
        for a,b in zip(baseline["cells"],paired["cells"]):
            self.assertEqual(a["methods"]["mi_zero"],b["methods"]["mi_zero"])
            self.assertEqual(b["methods"]["oracle_full"]["fitted"],2)
            self.assertEqual(b["methods"]["oracle_ipw"]["fitted"],2)
            self.assertEqual(b["paired_against_full"]["mi_zero"]["paired"],2)

    def test_paired_difference_counts_only_valid_pairs(self):
        a=dict(beta=.1,ci95=[0,.2],p=.1)
        b=dict(beta=.2,ci95=[.1,.3],p=.1)
        result=paired_difference([a,None,b],[b,a,a])
        self.assertEqual(result["paired"],2)
        self.assertAlmostEqual(result["mean_difference"],0.)
        self.assertAlmostEqual(result["mcse"],.1)
        with self.assertRaises(ValueError):
            paired_difference([a],[])

    def test_complete_shift_invariance(self):
        a = run("complete",reps=2,m=2,sweeps=1,target=100,cap=160,reference_n=1000)
        for c in a["cells"]:
            self.assertEqual(c["methods"]["mi_zero"],c["methods"]["mi_slope_minus2"])
            self.assertEqual(c["methods"]["mi_zero"],c["methods"]["mi_slope_plus2"])


if __name__ == "__main__":
    unittest.main()
