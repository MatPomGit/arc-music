import unittest
from unittest.mock import patch
import numpy as np
from augmented_candidate import augmented_arm,augmented_point,augmented_family
from assignment_candidate import point
from inference import prepare
from test_inference import fixture
from calibration import generate

class AugmentedTests(unittest.TestCase):
    def test_complete_reduces_to_unadjusted_mean(self):
        d=prepare(fixture())
        y,_=augmented_point(d,"understanding2")
        self.assertAlmostEqual(y,point(d,"understanding2")[0])
    def test_linear_outcome_and_constant_response(self):
        d=generate(np.random.default_rng(42),440,"standard","complete","null")
        a=d[d.music==0].copy()
        a["understanding2"]=1+.5*a.understanding0
        truth=a.understanding2.mean()
        a.loc[a.index[::3],"understanding2"]=np.nan
        with patch("augmented_candidate.response_probability",return_value=np.full(len(a),2/3)):
            estimate,diag=augmented_arm(a,"understanding2")
        self.assertAlmostEqual(estimate,truth)
        self.assertFalse(diag["positivity_warning"])
    def test_rank_failure_and_unknown_target(self):
        d=prepare(fixture())
        a=d[d.music==0].copy()
        a["understanding0"]=5.
        a.loc[a.index[0],"understanding2"]=np.nan
        with self.assertRaisesRegex(ValueError,"rank/size"):
            augmented_arm(a,"understanding2")
        d["target_status2"]="unknown"
        with patch("augmented_candidate.augmented_point",return_value=(.2,[{"positivity_warning":True}])):
            report=augmented_family(d,reps=199)
        self.assertFalse(report["hypotheses"]["H1"]["candidate_available"])
        self.assertEqual(report["hypotheses"]["H1"]["attempted"],0)
        self.assertFalse(report["confirmatory_available"])
