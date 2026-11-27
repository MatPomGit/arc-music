import unittest
import numpy as np
from test_inference import fixture
from inference import prepare,fit_arrays,PRED
from sensitivity import assess,weighted_slope
class TestSensitivity(unittest.TestCase):
    def test_equal_weights(self):
        _,a=prepare(fixture())
        g=a.participant_id.to_numpy();x=a[PRED].to_numpy(float);y=a.valence60.to_numpy(float)
        self.assertAlmostEqual(weighted_slope(g,x,y,np.ones(len(y)))[0],fit_arrays(g,x,y)["beta"],places=10)
    def test_separate_missingness(self):
        d=fixture();d["creation_first_hour"]=d.creation_first_hour.astype(object)
        d.loc[[0,1],"creation_first_hour"]=None;d.loc[[1,2],"valence60"]=np.nan
        a,_=prepare(d);r=assess(a,draws=5)
        self.assertEqual(r["unknown_exposure"],2)
        self.assertEqual(r["unknown_outcome"],2)
        self.assertEqual(r["both_missing"],1)
        self.assertEqual(len(r["outcome_shifts"]["scenarios"]),15)
        self.assertEqual(len(r["exposure_shifts"]["log_odds_shifts"]),3)
        self.assertEqual(r,assess(a,draws=5))
    def test_late_exposure_masked(self):
        d=fixture();d.loc[0,"exposure_time"]=d.loc[0,"baseline_time"]
        a,_=prepare(d);self.assertEqual(assess(a,draws=3)["unknown_exposure"],1)
    def test_no_missing(self):
        a,_=prepare(fixture());r=assess(a,draws=3)
        self.assertEqual(r["unknown_exposure"],0)
        self.assertIn("unavailable",r["exposure_shifts"])
    def test_no_complete_windows_reports_unavailable(self):
        raw=fixture()
        raw["valence60"]=np.nan
        d,_=prepare(raw)
        result=assess(d,draws=2)
        self.assertEqual(result["unknown_outcome"],400)
        for key in ("stage_ipw","outcome_shifts","exposure_shifts"):
            self.assertIn("No complete",result[key]["unavailable"])
    def test_no_unknown_exposure_precedes_logistic_fit(self):
        raw=fixture()
        raw["creation_first_hour"]=False
        d,_=prepare(raw)
        result=assess(d,draws=2)
        self.assertEqual(result["exposure_shifts"]["unavailable"],
                         "No unknown exposure among valid outcomes")
if __name__=="__main__":unittest.main()
