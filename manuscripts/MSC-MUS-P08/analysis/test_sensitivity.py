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
