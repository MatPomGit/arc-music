import unittest
from unittest.mock import patch
import pandas as pd
from withdrawal_audit import audit
from analyze import analyze
from test_ledger import row


class WithdrawalTests(unittest.TestCase):
    def fixture(self):
        e=pd.DataFrame([dict(participant_id="p",first_day="2026-11-01",
             timezone="Europe/Warsaw",withdrawal_time="2026-11-02T10:30:00+01:00",
             withdrawal_day="2026-11-03")])
        c=pd.DataFrame([dict(participant_id="p",local_day="2026-11-01",
              reported_sessions=1,checkin_time="2026-11-01T20:00:00+01:00")])
        return e,c,pd.DataFrame([row()])
    def test_before_cutoff(self):
        e,c,s=self.fixture()
        self.assertTrue(audit(e,c,s)["timestamp_gate_passed"])
        s["followup_time"]="2026-11-02T09:29:59Z"
        self.assertTrue(audit(e,c,s)["timestamp_gate_passed"])
    def test_at_or_after_cutoff_every_event(self):
        for event in ("pre_time","start_time","end_time","post_time","followup_time"):
            for stamp in ("2026-11-02T09:30:00Z","2026-11-02T10:31:00+01:00"):
                e,c,s=self.fixture()
                s[event]=stamp
                with self.assertRaisesRegex(ValueError,"withdrawal cutoff"):audit(e,c,s)
    def test_required_ledger_and_timestamp(self):
        e,c,s=self.fixture()
        with patch("analyze.fit_arrays") as fit:
            with self.assertRaisesRegex(ValueError,"requires enrollment"):analyze(s,data_kind="empirical")
            fit.assert_not_called()
        s["followup_time"]=None
        with self.assertRaisesRegex(ValueError,"lacks event"):audit(e,c,s)
        e,c,s=self.fixture()
        c["checkin_time"]=None
        with self.assertRaisesRegex(ValueError,"lacks timestamp"):audit(e,c,s)
    def test_unknown_id_and_inconsistent_day(self):
        e,c,s=self.fixture()
        s["participant_id"]="q"
        with self.assertRaisesRegex(ValueError,"Unknown participant"):audit(e,c,s)
        e,c,s=self.fixture()
        e["withdrawal_day"]="2026-11-02"
        with self.assertRaisesRegex(ValueError,"contradicts"):audit(e,c,s)
    def test_missing_cutoff(self):
        e,c,s=self.fixture()
        e["withdrawal_time"]=None
        with self.assertRaisesRegex(ValueError,"exact cutoff"):audit(e,c,s)
    def test_checkin_at_cutoff(self):
        e,c,s=self.fixture()
        c["local_day"]="2026-11-02"
        c["checkin_time"]="2026-11-02T09:30:00Z"
        with self.assertRaisesRegex(ValueError,"withdrawal cutoff"):audit(e,c,s)
