import unittest
import numpy as np
from inference import prepare,fit
from sensitivity import assess,cell_bounds
from test_inference import fixture
class TestSensitivity(unittest.TestCase):
    def test_no_missing(self):
        d=prepare(fixture());r=assess(d,"ownership")
        self.assertAlmostEqual(r["ipw"]["point_estimates"]["10"]["authority"],fit(d,"ownership")["authority"]["beta"],places=10)
        self.assertAlmostEqual(*r["unadjusted_hypothetical_bounds"]["authority"],places=10)
    def test_missing_and_bounds(self):
        f=fixture();f.loc[0,"heard_version"]=False;f.loc[101,"ownership1"]=np.nan
        d=prepare(f);r=assess(d,"ownership")
        self.assertEqual(r["missing"],2)
        self.assertEqual(len(r["shift_scenarios"]),27)
        lo,hi=r["unadjusted_hypothetical_bounds"]["authority"]
        self.assertAlmostEqual(hi-lo,.1)
        self.assertTrue(np.isfinite(r["ipw"]["point_estimates"]["20"]["interaction"]))
    def test_empty_observed_cell(self):
        f=fixture();f.loc[(f.authority==1)&(f.manual==1),"ownership1"]=np.nan
        r=assess(prepare(f),"ownership")
        self.assertIn("unavailable",r)
        self.assertIn("unadjusted_hypothetical_bounds",r)
if __name__=="__main__":unittest.main()

class TestHearingStatus(unittest.TestCase):
    def test_distinct_hypothetical_and_defined_populations(self):
        f = fixture()
        f["heard_version"] = f.heard_version.astype("boolean")
        f.loc[0, "heard_version"] = False
        f.loc[1, "heard_version"] = np.nan
        f.loc[2, "ownership1"] = np.nan
        audit = assess(prepare(f), "ownership")
        self.assertEqual(audit["exposure_status"], {
            "defined_observed": 397, "defined_missing": 1, "undefined": 1, "unknown": 1,
        })
        self.assertEqual(audit["heard_only_descriptive"]["missing"], 1)

    def test_bootstrap_refits_and_returns_finite_intervals(self):
        from sensitivity import bootstrap

        f = fixture()
        f.loc[:5, "ownership1"] = np.nan
        f.loc[100, "heard_version"] = False
        record = bootstrap(prepare(f), "ownership", 199, 8)
        self.assertEqual(record["valid"], 199)
        self.assertEqual(record["failures"], 0)
        self.assertEqual(len(record["shift"]), 27)
        low, high = record["ipw"]["20"]["authority"]
        self.assertLess(low, high)
        with self.assertRaises(ValueError):
            bootstrap(prepare(f), "ownership", 198, 8)
