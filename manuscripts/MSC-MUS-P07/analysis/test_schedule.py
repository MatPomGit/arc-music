import unittest
from datetime import datetime,timedelta,timezone
import pandas as pd
from schedule import generate,reconcile
from inference import analyze
class TestSchedule(unittest.TestCase):
    def fixture(self):
        return pd.DataFrame([dict(participant_id="p",first_day="2026-10-20",timezone="Europe/Warsaw",available_from="09:00",available_until="20:00"),
                             dict(participant_id="q",first_day="2026-10-20",timezone="Europe/Warsaw",available_from="09:00",available_until="20:00")])
    def test_seed_and_order(self):
        e=self.fixture()
        a=generate(e,2707);b=generate(e.iloc[::-1],2707)
        pd.testing.assert_frame_equal(a,b)
        self.assertEqual(len(a),42)
        self.assertEqual(a.window_id.nunique(),42)
        self.assertTrue((a.scheduled_time!=generate(e,2708).scheduled_time).any())
    def test_dst_and_horizon(self):
        a=generate(self.fixture(),2707)
        self.assertTrue(a.scheduled_time.str.endswith("+02:00").any())
        self.assertTrue(a.scheduled_time.str.endswith("+01:00").any())
        for s in a.scheduled_time:
            t=datetime.fromisoformat(s)
            self.assertLessEqual((t+timedelta(minutes=210)).hour*60+(t+timedelta(minutes=210)).minute,1200)
    def test_short_band(self):
        e=self.fixture();e.loc[0,"available_until"]="12:29"
        with self.assertRaisesRegex(ValueError,"210"):generate(e,1)
    def test_missing_preserved(self):
        s=generate(self.fixture(),2707)
        r=pd.DataFrame({"window_id":[s.iloc[0].window_id]})
        d=reconcile(s,r)
        self.assertEqual(len(d),42)
        self.assertEqual(d.response_record_received.sum(),1)
        result=analyze(r,schedule=s,sensitivity_draws=1)
        self.assertEqual(result["scheduled_without_response_record"],41)
        self.assertEqual(result["scheduled"],42)
    def test_unknown_window(self):
        s=generate(self.fixture(),1)
        with self.assertRaisesRegex(ValueError,"Unscheduled"):reconcile(s,pd.DataFrame({"window_id":["unknown"]}))
    def test_wrong_day_and_incomplete_schedule(self):
        s=generate(self.fixture(),1)
        r=pd.DataFrame({"window_id":[s.iloc[0].window_id],"study_day":[2]})
        with self.assertRaisesRegex(ValueError,"contradicts"):reconcile(s,r)
        with self.assertRaisesRegex(ValueError,"21"):reconcile(s.iloc[1:],pd.DataFrame({"window_id":[]}))
if __name__=="__main__":unittest.main()
