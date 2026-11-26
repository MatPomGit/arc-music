import unittest
import numpy as np
from test_inference import fixture
from inference import analyze,prepare,holm
import pandas as pd

def complete_fixture():
    d=fixture();rng=np.random.default_rng(42)
    d["followup180_time"]=(pd.to_datetime(d.baseline_time)+pd.Timedelta(hours=3)).map(lambda x:x.isoformat())
    d["valence180"]=np.clip(np.rint(3+.3*d.valence0+.6*d.creation_first_hour.astype(int)+rng.normal(0,.6,len(d))),0,10)
    d["desired_arousal0"]=rng.integers(3,8,len(d))
    d["arousal60"]=np.clip(d.desired_arousal0+np.where(d.creation_first_hour,1,3)+rng.integers(-1,2,len(d)),0,10)
    return d

class TestSecondary(unittest.TestCase):
    def test_recovery(self):
        r=analyze(complete_fixture())
        self.assertAlmostEqual(r["models"]["H2"]["estimate"]["beta"],.6,delta=.2)
        self.assertLess(r["models"]["H3"]["estimate"]["beta"],-1)
        self.assertEqual(len(r["secondary_holm"]),2)
    def test_h2_independent_of_h1(self):
        d=complete_fixture();d.loc[0,"valence60"]=np.nan
        r=analyze(d)
        self.assertEqual(r["models"]["H1"]["complete_windows"],399)
        self.assertEqual(r["models"]["H2"]["complete_windows"],400)
    def test_h3_missing_goal(self):
        d=complete_fixture();d.loc[0,"desired_arousal0"]=np.nan
        r=analyze(d)
        self.assertEqual(r["models"]["H3"]["complete_windows"],399)
        self.assertEqual(r["models"]["H1"]["complete_windows"],400)
    def test_late_h2(self):
        d=complete_fixture();d.loc[0,"followup180_time"]=d.loc[0,"followup60_time"]
        r=analyze(d)
        self.assertEqual(r["models"]["H2"]["complete_windows"],399)
    def test_missing_secondary_keeps_family(self):
        self.assertEqual(holm({"H2":.03,"H3":None}),{"H2":.06,"H3":None})
        self.assertEqual(holm({"H2":.04,"H3":.01}),{"H3":.02,"H2":.04})
    def test_narrow_window(self):
        d=complete_fixture()
        d.loc[0,"followup60_time"]=(pd.Timestamp(d.loc[0,"baseline_time"])+pd.Timedelta(minutes=70)).isoformat()
        r=analyze(d)
        self.assertEqual(r["models"]["H1"]["complete_windows"],400)
        self.assertEqual(r["timing_sensitivity"]["models"]["H1"]["complete_windows"],399)
    def test_optional_outcomes(self):
        r=analyze(fixture())
        self.assertIn("unavailable",r["models"]["H2"])
        self.assertIn("unavailable",r["models"]["H3"])
        self.assertIn("primary",r)
if __name__=="__main__":unittest.main()
