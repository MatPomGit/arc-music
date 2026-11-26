import unittest
import numpy as np
from fit_diagnostics import discrepancy_indices,from_fit
from robust_cfa import robust_fit
from recovery import simulate

class FitDiagnosticsTests(unittest.TestCase):
    def test_exact_correction(self):
        a=discrepancy_indices(20,10,110,30,501,model_expected=20,baseline_expected=30)
        self.assertEqual(a["cfi_like"],1.)
        self.assertEqual(a["tli_like"],1.)
        self.assertEqual(a["rmsea_like"],0.)
    def test_formula_and_undefined(self):
        a=discrepancy_indices(30,10,110,30,501)
        self.assertAlmostEqual(a["cfi_like"],.75)
        self.assertAlmostEqual(a["tli_like"],.25)
        self.assertAlmostEqual(a["rmsea_like"],np.sqrt(.004))
        b=discrepancy_indices(10,10,30,30,500)
        self.assertIsNone(b["cfi_like"])
        self.assertIsNone(b["tli_like"])
    def test_actual_fit(self):
        x=simulate(800,2,4,.65,.3,False,0.,np.random.default_rng(42))
        fit=robust_fit(x,np.repeat(np.arange(2),4))
        out=from_fit(fit)
        self.assertGreater(fit.baseline_statistic,fit.statistic)
        self.assertAlmostEqual(fit.baseline_expected,28.)
        self.assertFalse(out["trace_corrected"]["validated_wlsmv"])

if __name__=="__main__":
    unittest.main()
