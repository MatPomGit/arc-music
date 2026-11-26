import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
from factor_count_calibration import assess,run
from correlation_intervals import fisher_delta,compare_intervals

class RecoveryIntervals(unittest.TestCase):
    def test_selected_count_used(self):
        x=np.ones((100,9))
        pa=SimpleNamespace(retained=2,observed=np.ones(9),reference=np.ones(9))
        fit=SimpleNamespace(near_heywood=False,rms_residual=.02)
        with patch("factor_count_calibration.parallel_analysis",return_value=pa), patch("factor_count_calibration.polychoric_matrix",return_value=np.eye(9)), patch("factor_count_calibration.minres_promax",return_value=fit) as m:
            row=assess(x,3,3,.65,20)
            self.assertEqual(m.call_args.args[1],2)
            self.assertFalse(row["correct_count"])
            self.assertFalse(row["joint_recovery"])
    def test_zero_count(self):
        pa=SimpleNamespace(retained=0,observed=np.ones(9),reference=np.ones(9))
        with patch("factor_count_calibration.parallel_analysis",return_value=pa),patch("factor_count_calibration.minres_promax") as m:
            row=assess(np.ones((100,9)),3,3,.65,20)
            m.assert_not_called()
            self.assertEqual(row["status"],"no_factor")
    def test_smoke_seed(self):
        a=run(n=300,k=2,items=3,reps=1,pa_reps=10)
        b=run(n=300,k=2,items=3,reps=1,pa_reps=10)
        self.assertEqual(a,b)
        self.assertEqual(sum(a["selected_counts"].values()),1)
        self.assertFalse(a["protocol_permutations"])
    def test_fisher(self):
        out=fisher_delta(np.array([0.,.9,-.9]),np.array([.1,.1,.1]))
        self.assertTrue(np.all(abs(out)<1))
        self.assertAlmostEqual(out[0,0],-out[0,1])
        np.testing.assert_allclose(out[1],-out[2,::-1])
        with self.assertRaises(ValueError):
            fisher_delta(np.array([1.]),np.array([.1]))
    def test_bootstrap_failure_gate(self):
        f=SimpleNamespace(parameters=np.r_[np.full(6,.65),.35],covariance=np.eye(7)*.01,
                          intervals=np.tile([.1,.6],(7,1)))
        x=np.ones((100,6)); d=np.repeat(np.arange(2),3)
        with patch("correlation_intervals.robust_fit",side_effect=[f]*18+[ArithmeticError("failure")]*2):
            out=compare_intervals(x,d,reps=20,fit=f)
            self.assertEqual(out["proper"],18)
            self.assertIsNone(out["percentile"])
            self.assertIsNone(out["basic"])
            self.assertIsNotNone(out["fisher_delta"])

if __name__=="__main__":
    unittest.main()
