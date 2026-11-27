import unittest
import numpy as np
import pandas as pd
from inference import analyze,prepare,holm
from power import plan,power
def fixture():
    rng=np.random.default_rng(42);rows=[]
    for a in (0,1):
        for i in range(160):
            v=int(rng.integers(2,8));d=int(rng.integers(2,8))
            r=dict(participant_id=f"{a}-{i}",music=a,training=int(rng.integers(2)),prior_use_days=int(rng.integers(31)),importance0=int(rng.integers(11)),distance0=d,distance1=int(np.clip(np.rint(d+.6*a+rng.normal(0,.7)),0,10)),randomised_at="2026-11-01T10:00:00+01:00",t1_at="2026-11-01T10:15:00+01:00",t2_at="2026-11-08T10:00:00+01:00",same_event1=True,same_event2=True,target_status1="defined",target_status2="defined")
            for k in (1,2,3):
                r[f"understanding0{k}"]=v
                r[f"understanding1{k}"]=int(np.clip(np.rint(v+.7*a+rng.normal(0,.8)),0,10))
                r[f"understanding2{k}"]=int(np.clip(np.rint(v+.8*a+rng.normal(0,.8)),0,10))
            rows.append(r)
    return pd.DataFrame(rows)
class TestP09(unittest.TestCase):
    def test_recovery(self):
        r=analyze(fixture());self.assertAlmostEqual(r["hypotheses"]["H1"]["beta"],.8,delta=.2)
        self.assertAlmostEqual(r["hypotheses"]["H2"]["beta"],.7,delta=.2)
    def test_event_and_timing(self):
        d=fixture();d.loc[0,"same_event2"]=False;d.loc[1,"t1_at"]=d.loc[1,"t2_at"]
        r=prepare(d);self.assertTrue(pd.isna(r.iloc[0].understanding2));self.assertTrue(pd.isna(r.iloc[1].distance1))
        self.assertFalse(pd.isna(r.iloc[1].understanding2))
    def test_missing_item(self):
        d=fixture();d.loc[0,"understanding21"]=np.nan;r=analyze(d)
        self.assertEqual(r["randomised"],320);self.assertEqual(r["flow"]["0"]["observed"]["H1"],159)
        self.assertEqual(len(r["missingness"]["H1"]["shift_scenarios"]),25)
    def test_duplicate(self):
        d=fixture()
        with self.assertRaises(ValueError):prepare(pd.concat([d,d]))
    def test_holm(self):
        self.assertEqual(holm({"H2":.03,"H3":None}),{"H2":.06,"H3":None})
    def test_power(self):
        self.assertEqual(plan(.3)["complete"],470)
        self.assertEqual(plan(.3)["randomised"],588)
        self.assertLess(power(468,.3),.9)
if __name__=="__main__":unittest.main()
