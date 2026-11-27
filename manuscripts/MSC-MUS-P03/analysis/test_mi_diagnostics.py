import unittest
import numpy as np
from mi_diagnostics import diagnose, screen, scalar_summaries
from test_analysis import fixture
from models import prepare
from imputation import draw_imputations


class DiagnosticsTests(unittest.TestCase):
    def test_independent_and_separated_chains(self):
        rng=np.random.default_rng(42)
        x=rng.normal(size=(8,160))
        self.assertEqual(diagnose(x)["status"],"screen_pass")
        x[:4]+=5
        self.assertEqual(diagnose(x)["status"],"screen_flag")
        self.assertGreater(diagnose(x)["rhat"],1.01)

    def test_invalid_constant_and_short_traces(self):
        self.assertEqual(diagnose(np.ones((4,40)))["status"],"constant_trace")
        self.assertEqual(diagnose(np.ones((3,40)))["status"],"insufficient_or_invalid")
        self.assertEqual(diagnose(np.ones((4,10)))["status"],"insufficient_or_invalid")

    def test_production_trace_coefficient(self):
        from models import fit
        raw=fixture(160)
        raw.loc[:20,"clarity_post"]=np.nan
        raw.loc[21:35,"motive_expression"]=np.nan
        d,_=prepare(raw)
        def trace(chain,sweep,w,mask):
            s=scalar_summaries(w,mask)
            self.assertAlmostEqual(s["H1:beta"],fit(w,"H1")["beta"],places=10)
            self.assertIn("clarity_post:cdf_5",s)
            self.assertIn("motive_expression:corr_clarity_post",s)
        list(draw_imputations(d,2,2,123,trace=trace))
        result=screen(d,chains=4,sweeps=22,burn=2,m=2,seed=123)
        self.assertEqual(result["status"],"screen_flag")
        self.assertFalse(result["confirmatory_authorized"])
        self.assertIsNotNone(result["terminal_mcse"])
