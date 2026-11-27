import unittest
import pandas as pd
import numpy as np
from simulation import draw
from inference import PREDICTORS,fit_arrays
from ledger import ledger
from test_ledger import row
from robustness import context_flags,robustness,confounding_grid
class TestRobustness(unittest.TestCase):
    def test_overlap_includes_nonprimary(self):
        a=row()
        b=row(session_id="s2",eligible_first=False,
              pre_time="2026-11-01T11:55:00+01:00",start_time="2026-11-01T12:00:00+01:00",
              end_time="2026-11-01T12:25:00+01:00",post_time=None,followup_time=None,interference=None)
        d=context_flags(ledger(pd.DataFrame([a,b])))
        self.assertTrue(d.iloc[0].later_start_during_endpoint)
        self.assertTrue(d.iloc[1].prior_start_24h)
        self.assertFalse(d.iloc[0].prior_start_24h)
    def test_no_cross_participant_overlap(self):
        d=context_flags(ledger(pd.DataFrame([row(),row(participant_id="q",session_id="s2")])))
        self.assertFalse(d.prior_start_24h.any())
        self.assertFalse(d.later_start_during_endpoint.any())
    def test_no_failure_field(self):
        r=robustness(ledger(pd.DataFrame([row()])))
        self.assertIn("unavailable",r["models"]["confirmed_no_technical_failure"])
        self.assertIn("unavailable",r["models"]["no_prior_logged_start"])
    def test_unknown_failure_not_assumed_false(self):
        d=ledger(pd.DataFrame([row(technical_failure=None)]))
        r=robustness(d)
        self.assertEqual(r["models"]["confirmed_no_technical_failure"]["excluded_sessions"],1)
    def test_confounding_grid_matches_primary_and_monotonicity(self):
        g,x,y=draw(np.random.default_rng(42),40,6,.3,missing=0)
        a=pd.DataFrame(x,columns=PREDICTORS)
        a["participant_id"]=g;a["interference"]=np.clip(np.rint(y),0,10)
        out=confounding_grid(a)
        self.assertAlmostEqual(out["observed_coefficient"],fit_arrays(g,x,a.interference)["estimate"][0])
        self.assertEqual(len(out["grid"]),16)
        self.assertLess(out["grid"][0]["absolute_coefficient_change"],out["grid"][-1]["absolute_coefficient_change"])
        self.assertTrue(out["not_confidence_intervals"])
if __name__=="__main__":unittest.main()
