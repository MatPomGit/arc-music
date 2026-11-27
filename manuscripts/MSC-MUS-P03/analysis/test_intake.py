import unittest
from io import StringIO
import numpy as np
import pandas as pd
from intake import select, read_records
from models import prepare, analyze
from test_analysis import fixture


class IntakeTests(unittest.TestCase):
    def test_boolean_and_canonical_csv(self):
        raw=fixture(30)
        raw.loc[1,"consent"]=False
        raw.loc[2,"eligible"]=False
        expected, _=prepare(raw)
        got,_=prepare(read_records(StringIO(raw.to_csv(index=False))))
        self.assertEqual(list(expected.study_id),list(got.study_id))
        self.assertEqual(got.attrs["intake_flow"]["accepted"],28)

    def test_bad_flag_is_local_and_no_sensitive_excluded_payload(self):
        raw=fixture(30)
        raw["consent"]=raw["consent"].astype(object)
        raw["eligible"]=raw["eligible"].astype(object)
        raw.loc[0,"consent"]="unknown"
        raw.loc[1,"consent"]=1
        raw.loc[2,"consent"]=np.nan
        raw.loc[3,"consent"]=False
        raw.loc[4,"eligible"]="1"
        raw.loc[5,"eligible"]=None
        raw.loc[6,"eligible"]="false"
        raw.loc[0,"clarity_post"]=999
        data,invalid=prepare(raw)
        self.assertEqual(len(data),23)
        self.assertEqual(invalid["clarity_post"],0)
        flow=data.attrs["intake_flow"]
        self.assertEqual(flow,{"submitted":30,"accepted":23,
            "consent_false":1,"consent_missing":1,"consent_invalid":2,
            "eligibility_false":1,"eligibility_missing":1,"eligibility_invalid":1})
        self.assertEqual(analyze(raw)["intake_flow"],flow)

    def test_bad_csv_token_does_not_change_other_rows(self):
        raw=fixture(30)
        raw["consent"]=raw["consent"].astype(object)
        raw.loc[0,"consent"]="unknown"
        raw.loc[1,"consent"]="1"
        raw.loc[2,"consent"]=""
        data,_=prepare(read_records(StringIO(raw.to_csv(index=False))))
        self.assertEqual(len(data),27)
        self.assertEqual(data.attrs["intake_flow"]["consent_invalid"],2)

    def test_required_and_invalid_ids(self):
        raw=fixture(30)
        with self.assertRaises(ValueError):
            prepare(raw.drop(columns="study_id"))
        for bad in (None,"","123","p04-00000000-0000-4000-8000-000000000001",
                    "p03-00000000-0000-1000-8000-000000000001"):
            data=raw.copy()
            data.loc[0,"study_id"]=bad
            with self.assertRaises(ValueError):
                prepare(data)

    def test_duplicate_with_excluded_record_fails_closed(self):
        raw=fixture(30)
        raw.loc[1,"study_id"]=raw.loc[0,"study_id"]
        raw.loc[1,"consent"]=False
        with self.assertRaises(ValueError):
            select(raw)
