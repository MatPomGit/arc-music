import unittest
from unittest.mock import patch
from invariance_power import run

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

if __name__=="__main__":
    unittest.main()
