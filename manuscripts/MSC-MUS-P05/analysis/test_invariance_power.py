import unittest
from unittest.mock import patch
from invariance_power import run, gate_rejected, summarize_gates

class PowerTests(unittest.TestCase):
    def test_failure_accounting(self):
        with patch("invariance_power.compare_groups",side_effect=ArithmeticError("failure")):
            out=run(1)
        self.assertEqual(len(out["scenarios"]),16)
        self.assertTrue(all(s["proper"]==0 and s["target_rate_conditional"] is None for s in out["scenarios"]))
    def test_balanced_unbalanced(self):
        f={"tests":{k:{"p_value":.01} for k in ("threshold_shape","threshold_loading","threshold_loading_intercept")},"ordered_gate":"threshold_shape_rejected"}
        with patch("invariance_power.compare_groups",return_value=f):
            out=run(1)
        self.assertEqual({tuple(s["sizes"]) for s in out["scenarios"]},{(250,250),(350,150),(400,400),(560,240)})
        self.assertTrue(all(s["target_rate_unconditional"]==1 for s in out["scenarios"]))

    def test_explicit_final_gate_statuses(self):
        for status in ("configural_rejected", "threshold_shape_rejected",
                       "threshold_loading_rejected", "threshold_loading_intercept_rejected"):
            with self.subTest(status=status):
                self.assertTrue(gate_rejected(status))
        self.assertFalse(gate_rejected("all_restrictions_not_rejected"))
        for status in ("configural_not_rejected", "unknown_rejected", None):
            with self.subTest(status=status), self.assertRaises(ValueError):
                gate_rejected(status)

    def test_nonrejection_and_failure_denominators(self):
        rows = [
            {"status": "proper", "ordered_gate": "threshold_shape_rejected"},
            {"status": "proper", "ordered_gate": "all_restrictions_not_rejected"},
            {"status": "failure", "reason": "synthetic failure"},
        ]
        s = summarize_gates(rows)
        self.assertEqual(s["failed"], 1)
        self.assertEqual(s["any_gate_rejected_count"], 1)
        self.assertEqual(s["any_gate_not_rejected_count"], 1)
        self.assertAlmostEqual(s["any_gate_rejection_unconditional"], 1/3)
        self.assertEqual(s["any_gate_rejection_conditional"], .5)
        self.assertIsNone(summarize_gates(rows[-1:])["any_gate_rejection_conditional"])

    def test_run_nonrejection_and_unknown(self):
        f = {"tests": {k: {"p_value": .5} for k in (
            "threshold_shape", "threshold_loading", "threshold_loading_intercept")},
             "ordered_gate": "all_restrictions_not_rejected"}
        with patch("invariance_power.compare_groups", return_value=f):
            out = run(1)
        self.assertTrue(all(s["any_gate_rejection_unconditional"] == 0
                            and s["any_gate_not_rejected_count"] == 1
                            for s in out["scenarios"]))
        f["ordered_gate"] = "unexpected_rejected"
        with patch("invariance_power.compare_groups", return_value=f):
            with self.assertRaises(ValueError):
                run(1)

if __name__=="__main__":
    unittest.main()
