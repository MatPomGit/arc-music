import unittest
import pandas as pd
import numpy as np
from ledger import ledger,analysis_ledger,flow_counts
from inference import eligible_rows
from analyze import analyze
from simulation import draw

def row(**overrides):
    r=dict(participant_id="p",session_id="s",local_day="2026-11-01",
           eligible_first=True,activity_defined=True,study_day=1,
           pre_time="2026-11-01T09:55:00+01:00",start_time="2026-11-01T10:00:00+01:00",
           end_time="2026-11-01T10:25:00+01:00",post_time="2026-11-01T10:30:00+01:00",
           followup_time="2026-11-02T10:25:00+01:00",avoidance=5,distress_pre=4,
           expected_difficulty=3,interference=2,distress_post=3,brooding=4)
    r.update(overrides)
    r.setdefault("activity_id","a-"+r["session_id"])
    r.setdefault("followup_activity_id",r["activity_id"])
    r.setdefault("activity_relevant",True)
    return r

class TestLedger(unittest.TestCase):
    def test_missing_followup_retained(self):
        d=pd.DataFrame([row(followup_time=None,interference=None)])
        a=analysis_ledger(d)
        self.assertEqual(len(a),1)
        self.assertEqual(a.iloc[0].followup_status,"no_followup")
        self.assertEqual(len(eligible_rows(d)),0)
    def test_missing_post_does_not_condition_primary(self):
        d=pd.DataFrame([row(post_time=None)])
        a=eligible_rows(d)
        self.assertEqual(len(a),1)
        self.assertTrue(pd.isna(a.iloc[0].brooding))
    def test_late_post_masked(self):
        a=eligible_rows(pd.DataFrame([row(post_time="2026-11-01T11:00:00+01:00")]))
        self.assertEqual(len(a),1)
        self.assertFalse(a.iloc[0].post_valid)
        self.assertTrue(pd.isna(a.iloc[0].distress_post))
    def test_late_pre_excluded(self):
        d=ledger(pd.DataFrame([row(pre_time="2026-11-01T10:01:00+01:00")]))
        self.assertEqual(d.iloc[0].session_status,"invalid_pre")
    def test_missing_end_excluded(self):
        d=ledger(pd.DataFrame([row(end_time=None)]))
        self.assertEqual(d.iloc[0].session_status,"invalid_session")
    def test_followup_anchor_is_end(self):
        d=ledger(pd.DataFrame([row(followup_time="2026-11-02T14:26:00+01:00")]))
        self.assertEqual(d.iloc[0].followup_status,"outside_window")
        self.assertTrue(pd.isna(d.iloc[0].interference))
    def test_local_day_offset(self):
        with self.assertRaisesRegex(ValueError,"local day"):
            ledger(pd.DataFrame([row(local_day="2026-10-31")]))
    def test_first_flag_contradiction(self):
        d=pd.DataFrame([row(),row(session_id="s2",eligible_first=False,
            start_time="2026-11-01T09:00:00+01:00")])
        with self.assertRaisesRegex(ValueError,"contradicts"):
            ledger(d)
    def test_early_followup_is_missing(self):
        a=analysis_ledger(pd.DataFrame([row(followup_time="2026-11-02T09:25:00+01:00")]))
        self.assertEqual(len(a),1)
        self.assertEqual(a.iloc[0].followup_status,"outside_window")
        self.assertTrue(pd.isna(a.iloc[0].interference))
    def test_activity_mismatch(self):
        a=analysis_ledger(pd.DataFrame([row(followup_activity_id="another")]))
        self.assertEqual(a.iloc[0].followup_status,"activity_mismatch")
        self.assertTrue(pd.isna(a.iloc[0].interference))
    def test_activity_no_longer_relevant(self):
        a=analysis_ledger(pd.DataFrame([row(activity_relevant=False)]))
        self.assertEqual(a.iloc[0].followup_status,"activity_no_longer_relevant")
        self.assertTrue(pd.isna(a.iloc[0].interference))
    def test_unknown_relevance(self):
        a=analysis_ledger(pd.DataFrame([row(activity_relevant=None)]))
        self.assertEqual(a.iloc[0].followup_status,"relevance_unknown")
    def test_narrow_window(self):
        d=pd.DataFrame([row(followup_time="2026-11-02T13:25:00+01:00")])
        self.assertEqual(ledger(d).iloc[0].followup_status,"observed")
        self.assertEqual(ledger(d,upper_hours=26).iloc[0].followup_status,"outside_window")
    def test_reused_activity_token(self):
        d=pd.DataFrame([row(),row(session_id="s2",activity_id="a-s",eligible_first=False)])
        with self.assertRaisesRegex(ValueError,"identifier reused"):
            ledger(d)
    def test_end_to_end(self):
        g,x,y=draw(np.random.default_rng(42),40,6,.3,missing=0)
        rows=[]
        for i,(person,v,outcome) in enumerate(zip(g,x,y)):
            day=int(v[3]); date=f"2026-11-{day:02d}"
            nextdate=f"2026-11-{day+1:02d}"
            rows.append(row(participant_id=str(person),session_id=str(i),study_day=day,local_day=date,
                pre_time=date+"T09:55:00+01:00",start_time=date+"T10:00:00+01:00",
                end_time=date+"T10:25:00+01:00",post_time=date+"T10:30:00+01:00",
                followup_time=nextdate+"T10:25:00+01:00",
                avoidance=v[0],distress_pre=v[1],expected_difficulty=v[2],
                interference=None if i%4==0 else np.clip(np.rint(outcome),0,10),
                distress_post=i%11,brooding=(i*3)%11))
        r=analyze(pd.DataFrame(rows),reps=5)
        self.assertEqual(r["flow"]["eligible_sessions"],240)
        self.assertEqual(r["flow"]["followup_status"]["missing_score"],60)
        self.assertEqual(r["missingness"]["reps"],5)
        self.assertEqual(len(r["secondary"]),3)

if __name__=="__main__":unittest.main()
