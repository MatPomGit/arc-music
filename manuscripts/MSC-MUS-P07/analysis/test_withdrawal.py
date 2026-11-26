import unittest
import pandas as pd
from schedule import generate,reconcile
from withdrawal import apply_withdrawal
from inference import analyze
class TestWithdrawal(unittest.TestCase):
    def fixture(self):
        e=pd.DataFrame([dict(participant_id="p",first_day="2026-11-01",timezone="Europe/Warsaw",available_from="09:00",available_until="20:00")])
        s=generate(e,2707)
        w=pd.DataFrame([dict(participant_id="p",withdrawal_time="2026-11-06T00:00:00+01:00")])
        r=pd.DataFrame({"window_id":[]})
        return s,r,w
    def test_denominators(self):
        s,r,w=self.fixture();out=analyze(r,schedule=s,withdrawals=w,sensitivity_draws=1)
        self.assertEqual(out["scheduled"],21)
        self.assertEqual(out["withdrawal_flow"]["active_prompt_windows"],5)
        self.assertEqual(out["status"]["cancelled_after_withdrawal"],16)
        self.assertEqual(out["status"]["baseline_unavailable"],5)
    def test_midwindow(self):
        s,r,w=self.fixture()
        stamp=pd.Timestamp(s.iloc[0].scheduled_time)
        w.loc[0,"withdrawal_time"]=(stamp+pd.Timedelta(minutes=90)).isoformat()
        r=pd.DataFrame([dict(window_id=s.iloc[0].window_id,baseline_time=stamp.isoformat())])
        d=apply_withdrawal(reconcile(s,r),w)
        self.assertTrue(d.iloc[0].withdrawal_during_window)
        self.assertFalse(d.iloc[0].withdrawn_before_prompt)
    def test_late_response(self):
        s,r,w=self.fixture()
        r=pd.DataFrame([dict(window_id=s.iloc[5].window_id,baseline_time=s.iloc[5].scheduled_time)])
        with self.assertRaisesRegex(ValueError,"after withdrawal"):
            apply_withdrawal(reconcile(s,r),w)
    def test_unknown_participant(self):
        s,r,w=self.fixture();w.loc[0,"participant_id"]="q"
        with self.assertRaisesRegex(ValueError,"Unknown"):
            apply_withdrawal(reconcile(s,r),w)
    def test_empty_verified_log(self):
        s,r,w=self.fixture();out=analyze(r,schedule=s,withdrawals=w.iloc[:0],sensitivity_draws=1)
        self.assertEqual(out["withdrawal_flow"]["active_prompt_windows"],21)
    def test_exact_cutoff(self):
        s,r,w=self.fixture();w.loc[0,"withdrawal_time"]=s.iloc[0].scheduled_time
        out=apply_withdrawal(reconcile(s,r),w)
        self.assertTrue(out.withdrawn_before_prompt.all())
if __name__=="__main__":unittest.main()
