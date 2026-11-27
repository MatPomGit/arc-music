import unittest
from unittest.mock import patch
import numpy as np
from assignment_candidate import candidate_test, candidate_family, centered_test
from inference import prepare
from test_inference import fixture


class CandidateTests(unittest.TestCase):
    def test_centered_test_and_interval(self):
        draws = np.linspace(.7, 1.3, 199)
        result = centered_test(1., draws)
        self.assertAlmostEqual(result["p"], 1/200)
        self.assertGreater(result["ci"][0], 0)
        self.assertGreater(centered_test(0., draws-1)["p"], .05)
        with self.assertRaises(ValueError):
            centered_test(1., np.ones(199))

    def test_partial_defined_and_wrong_event(self):
        frame = fixture()
        frame.loc[0,"understanding21"] = np.nan
        frame.loc[1,"same_event2"] = False
        d = prepare(frame)
        self.assertEqual(d.understanding2.isna().sum(), 2)
        result = candidate_test(d, "understanding2", "target_status2", reps=199, seed=13)
        self.assertTrue(result["candidate_available"], result)
        self.assertFalse(result["confirmatory_available"])
        self.assertEqual(result["successful"]+result["failed"], 199)
        self.assertEqual(result["attempted"], 199)

    def test_undefined_and_unknown_never_tested(self):
        for status in ("undefined", "unknown"):
            frame = fixture()
            frame.loc[0,"target_status2"] = status
            frame.loc[0,["understanding21","understanding22","understanding23"]] = np.nan
            result = candidate_test(prepare(frame), "understanding2", "target_status2", reps=199)
            self.assertFalse(result["candidate_available"])
            self.assertEqual(result["attempted"], 0)
            self.assertNotIn("candidate_p", result)

    def test_overlap_and_failure_gate(self):
        d = prepare(fixture())
        with patch("assignment_candidate.point", return_value=(.5,[{"positivity_warning":True}])):
            result = candidate_test(d,"understanding2","target_status2",199)
        self.assertEqual(result["attempted"],0)
        self.assertFalse(result["candidate_available"])
        with patch("assignment_candidate.point", side_effect=[(.5,[{"positivity_warning":False}])]
                   +[ValueError("synthetic failure")]*199):
            result = candidate_test(d,"understanding2","target_status2",199)
        self.assertEqual(result["failed"],199)
        self.assertFalse(result["candidate_available"])

    def test_fixed_secondary_family_and_no_authorization(self):
        d = prepare(fixture())
        available = {"candidate_p":.03,"candidate_available":True}
        unavailable = {"candidate_available":False}
        with patch("assignment_candidate.candidate_test", side_effect=[available,available,unavailable]):
            result = candidate_family(d)
        self.assertEqual(result["candidate_secondary_holm"],{"H2":.06,"H3":None})
        self.assertFalse(result["confirmatory_available"])


if __name__ == "__main__":
    unittest.main()
