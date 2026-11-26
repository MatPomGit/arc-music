import unittest
import pandas as pd
import numpy as np
from inference import prepare,analyze
def fixture():
    rng=np.random.default_rng(16); rows=[]
    for i in range(40):
        for d in range(1,11):
            a,b,c=rng.integers(1,8,size=3); z=bool(d%2)
            hour=int(rng.integers(9,15)); stamp=pd.Timestamp(f"2026-11-{d:02d}T{hour:02d}:00:00+01:00")
            rows.append(dict(participant_id=str(i),window_id=f"{i}-{d}",study_day=d,scheduled_time=stamp.isoformat(),baseline_time=stamp.isoformat(),exposure_time=(stamp+pd.Timedelta(hours=1)).isoformat(),followup60_time=(stamp+pd.Timedelta(hours=1)).isoformat(),creation_ongoing=False,creation_first_hour=z,valence0=a,arousal0=b,intention0=c,valence60=np.clip(np.rint(3+.3*a+.8*z+rng.normal(0,.6)),0,10)))
    return pd.DataFrame(rows)
class TestP07(unittest.TestCase):
    def test_recovery(self):
        r=analyze(fixture())
        self.assertEqual(r["primary"]["switchers"],40)
        self.assertAlmostEqual(r["primary"]["beta"],.8,delta=.2)
    def test_missing_exposure(self):
        d=fixture();d["creation_first_hour"]=d.creation_first_hour.astype(object);d.loc[0,"creation_first_hour"]=None
        a,b=prepare(d);self.assertEqual(a.iloc[0].status,"exposure_unavailable");self.assertEqual(len(b),399)
    def test_ongoing(self):
        d=fixture();d.loc[0,"creation_ongoing"]=True
        a,b=prepare(d);self.assertEqual(len(b),399)
    def test_early(self):
        d=fixture();d.loc[0,"followup60_time"]=d.loc[0,"baseline_time"]
        a,b=prepare(d);self.assertEqual(a.iloc[0].status,"outcome_unavailable")
    def test_duplicate(self):
        d=fixture()
        with self.assertRaisesRegex(ValueError,"Duplicate"):prepare(pd.concat([d,d]))
    def test_missing_scheduled(self):
        d=fixture();d.loc[0,"scheduled_time"]=None
        with self.assertRaisesRegex(ValueError,"Missing schedule"):prepare(d)
if __name__=="__main__":unittest.main()
