import json
import unittest
import numpy as np
from test_inference import fixture
from inference import prepare,fit
from joint_sensitivity import assess_joint

class JointSensitivityTests(unittest.TestCase):
    def test_complete_reproduces_primary(self):
        d,a=prepare(fixture())
        out=assess_joint(d,draws=3)
        self.assertAlmostEqual(out["complete_case_beta"],fit(a)["beta"],places=10)
        for result in out["scenarios"].values():
            self.assertEqual(result["valid"],3)
            self.assertAlmostEqual(result["median"],fit(a)["beta"],places=10)
    def test_joint_missing_and_denominators(self):
        raw=fixture()
        raw["creation_first_hour"]=raw.creation_first_hour.astype(object)
        raw.loc[[0,1],"creation_first_hour"]=None
        raw.loc[[1,2],"valence60"]=np.nan
        raw.loc[raw.participant_id.eq("3"),"valence60"]=np.nan
        d,_=prepare(raw)
        out=assess_joint(d,draws=4,seed=3)
        self.assertEqual(out["both_missing_included"],1)
        self.assertEqual(out["excluded_participants"],1)
        self.assertEqual(out["excluded_windows"],10)
        self.assertEqual(len(out["scenarios"]),9)
        for result in out["scenarios"].values():
            self.assertEqual(result["valid"]+result["failed"],4)
        self.assertEqual(out,assess_joint(d,draws=4,seed=3))
        json.dumps(out,allow_nan=False)
    def test_no_complete_fails_explicitly(self):
        raw=fixture()
        raw["valence60"]=np.nan
        d,_=prepare(raw)
        with self.assertRaisesRegex(ValueError,"No complete"):
            assess_joint(d,draws=1)
