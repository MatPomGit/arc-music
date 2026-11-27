import unittest

import numpy as np

from imputation_calibration import mask_and_stop, raw_records, run, summary, mixed_mar_attainment
from stress import generate


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

    def test_small_reproducible_production_screen(self):
        kw = dict(reps=2,m=2,sweeps=1,target=100,cap=160,reference_n=1000)
        a = run("mixed_mar",**kw)
        self.assertEqual(a,run("mixed_mar",**kw))
        for c in a["cells"]:
            for v in c["methods"].values():
                self.assertEqual(v["fitted"]+v["failures"],2)
                self.assertEqual(v["fitted"],2)

    def test_complete_shift_invariance(self):
        a = run("complete",reps=2,m=2,sweeps=1,target=100,cap=160,reference_n=1000)
        for c in a["cells"]:
            self.assertEqual(c["methods"]["mi_zero"],c["methods"]["mi_slope_minus2"])
            self.assertEqual(c["methods"]["mi_zero"],c["methods"]["mi_slope_plus2"])


if __name__ == "__main__":
    unittest.main()
