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

    def test_optional_payload_requires_own_timestamp(self):
        for event,field,value in (
            ("post_time","technical_failure",False),("post_time","generation_count",0),
            ("post_time","duration_minutes",0),("followup_time","activity_status_reason","unknown"),
            ("followup_time","followup_missing_reason","skipped"),
            ("followup_time","activity_completed",False),("pre_time","activity_id","a-opaque")):
            from withdrawal_audit import PAYLOADS
            e,c,s=self.fixture()
            s[event]=None
            for k in PAYLOADS[event]:
                if k in s:s[k]=None
            s[field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,"lacks event timestamp"):
                audit(e,c,s)
    def test_before_enrollment_and_missing_event_column(self):
        e,c,s=self.fixture()
        s["pre_time"]="2026-10-31T23:59:59+01:00"
        with self.assertRaisesRegex(ValueError,"precedes first enrolled"):
            audit(e,c,s)
        e,c,s=self.fixture()
        with self.assertRaisesRegex(ValueError,"Missing authoritative session time fields"):
            audit(e,c,s.drop(columns="post_time"))
    def test_csv_contract_preserves_flags_and_identifiers(self):
        from export_schema import read_export,fields
        from pathlib import Path
        from tempfile import TemporaryDirectory
        e,c,s=self.fixture()
        e["participant_id"]=c["participant_id"]=s["participant_id"]="0001"
        s["session_id"]="0002"
        s["activity_id"]=s["followup_activity_id"]="0003"
        s["technical_failure"]=False
        s["activity_completed"]=None
        for k in fields("sessions")-set(s):s[k]=None
        with TemporaryDirectory() as tmp:
            folder=Path(tmp)
            frames={}
            for kind,data in (("sessions",s),("enrollment",e),("checkins",c)):
                path=folder/(kind+".csv")
                data.to_csv(path,index=False)
                frames[kind]=read_export(path,kind,empirical=True)
            actual=frames["sessions"]
            self.assertEqual(actual.participant_id.iloc[0],"0001")
            self.assertEqual(actual.activity_id.iloc[0],"0003")
            self.assertFalse(actual.technical_failure.iloc[0])
            self.assertTrue(pd.isna(actual.activity_completed.iloc[0]))
            self.assertTrue(audit(frames["enrollment"],frames["checkins"],actual)["timestamp_gate_passed"])
            path=folder/"sessions.csv"
            for token in ("0","yes","FALSE","null"," "):
                bad=s.copy();bad["technical_failure"]=token;bad.to_csv(path,index=False)
                with self.assertRaisesRegex(ValueError,"Invalid flag"):
                    read_export(path,"sessions",empirical=True)
            s.assign(extra=1).to_csv(path,index=False)
            with self.assertRaisesRegex(ValueError,"field mismatch"):
                read_export(path,"sessions",empirical=True)
            s.to_csv(path,index=False)
            path.write_text(path.read_text().replace("participant_id,","participant_id,participant_id,",1))
            with self.assertRaisesRegex(ValueError,"duplicate CSV fields"):
                read_export(path,"sessions",empirical=True)
