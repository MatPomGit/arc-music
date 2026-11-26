import unittest
import pandas as pd
from daily import daily_ledger,summarize
from ledger import ledger
from test_ledger import row

class TestDaily(unittest.TestCase):
    def fixture(self):
        e=pd.DataFrame([dict(participant_id="p",first_day="2026-11-01",withdrawal_day="2026-11-06"),
                        dict(participant_id="q",first_day="2026-11-01",withdrawal_day=None)])
        c=pd.DataFrame([dict(participant_id="p",local_day="2026-11-01",reported_sessions=2),
                        dict(participant_id="p",local_day="2026-11-02",reported_sessions=0),
                        dict(participant_id="p",local_day="2026-11-03",reported_sessions=None)])
        s=ledger(pd.DataFrame([row()]))
        return e,c,s
    def test_denominators(self):
        d=daily_ledger(*self.fixture())
        r=summarize(d)
        self.assertEqual(r["scheduled_days"],28)
        self.assertEqual(r["active_days"],19)
        self.assertEqual(r["received_checkins"],3)
        self.assertEqual(r["day_status"]["confirmed_no_creation"],1)
        self.assertEqual(r["day_status"]["unknown_no_checkin"],16)
        self.assertEqual(r["reported_unlogged_lower_bound"],1)
    def test_conflict(self):
        e,c,s=self.fixture()
        c.loc[0,"reported_sessions"]=0
        self.assertEqual(summarize(daily_ledger(e,c,s))["count_conflicts"],1)
    def test_unknown_not_zero(self):
        e,c,s=self.fixture()
        c=c.iloc[0:0]
        r=summarize(daily_ledger(e,c,s))
        self.assertEqual(r["day_status"]["logged_without_count"],1)
        self.assertNotIn("confirmed_no_creation",r["day_status"])
    def test_withdrawal(self):
        e,c,s=self.fixture()
        c.loc[0,"local_day"]="2026-11-06"
        with self.assertRaisesRegex(ValueError,"withdrawal"):
            daily_ledger(e,c,s)
    def test_study_day_mismatch(self):
        e,c,s=self.fixture()
        s.loc[0,"study_day"]=2
        with self.assertRaisesRegex(ValueError,"contradicts"):
            daily_ledger(e,c,s)
    def test_outside_window(self):
        e,c,s=self.fixture()
        c.loc[0,"local_day"]="2026-12-01"
        with self.assertRaisesRegex(ValueError,"outside"):
            daily_ledger(e,c,s)
    def test_duplicate_checkin(self):
        e,c,s=self.fixture()
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            daily_ledger(e,pd.concat([c,c]),s)
    def test_invalid_count(self):
        e,c,s=self.fixture()
        c.loc[0,"reported_sessions"]=-1
        with self.assertRaisesRegex(ValueError,"Invalid reported"):
            daily_ledger(e,c,s)

if __name__=="__main__":unittest.main()
