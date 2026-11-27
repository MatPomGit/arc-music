import unittest
from unittest.mock import patch
import numpy as np
from mi_diagnostics import diagnose, screen, scalar_summaries, compare_sweeps
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

    def test_ragged_and_nonfinite_traces(self):
        for x in ([[0.]*40,[1.]*39,[2.]*40,[3.]*40],
                  np.full((4,40),np.nan), np.full((4,40),np.inf)):
            self.assertEqual(diagnose(x)["status"],"insufficient_or_invalid")

    def test_missing_and_duplicate_callbacks_fail_closed(self):
        for mode in ("missing","duplicate"):
            def fake_draw(data,m,sweeps,seed,trace=None):
                for chain in range(m):
                    for sweep in range(sweeps):
                        if mode=="missing" and chain==0 and sweep==2:
                            continue
                        trace(chain,sweep,None,None)
                        if mode=="duplicate" and chain==0 and sweep==2:
                            trace(chain,sweep,None,None)
                    yield None,None
            with patch("mi_diagnostics.draw_imputations",side_effect=fake_draw), \
                 patch("mi_diagnostics.scalar_summaries",return_value={"H1:beta":0.1}):
                result=screen(None,chains=4,sweeps=22,burn=2,m=2)
            self.assertEqual(result["status"],"execution_failure")
            self.assertFalse(result["confirmatory_authorized"])

    def test_paired_checkpoints_share_trajectories(self):
        calls=[]
        def fake_draw(data,m,sweeps,seed,trace=None):
            calls.append((m,sweeps,seed))
            for chain in range(m):
                for sweep in range(sweeps):
                    trace(chain,sweep,(chain,sweep),None)
                yield None,None
        def fitted(work,h):
            chain,sweep=work
            return dict(beta=.1+chain*.01+sweep*.001,se_hc3=.05,n=100)
        with patch("mi_diagnostics.draw_imputations",side_effect=fake_draw), \
             patch("mi_diagnostics.scalar_summaries",side_effect=lambda w,m:{"H1:beta":float(w[0]+w[1])}), \
             patch("mi_diagnostics.fit",side_effect=fitted):
            result=compare_sweeps(None,(22,42),burn=2,chains=4,m=2,seed=7)
        self.assertEqual(calls,[(4,42,7),(2,42,8)])
        self.assertTrue(result["paired_prefixes"])
        rows=result["checkpoints"]
        self.assertEqual([r["retained_draws"] for r in rows],[80,160])
        self.assertAlmostEqual(rows[1]["pooled_beta"]-rows[0]["pooled_beta"],.020)
        self.assertFalse(result["confirmatory_authorized"])
        with self.assertRaises(ValueError):
            compare_sweeps(None,(42,22),burn=2)

    def test_single_checkpoint_matches_public_screen(self):
        raw=fixture(100)
        raw.loc[:8,"clarity_post"]=np.nan
        data,_=prepare(raw)
        a=screen(data,chains=4,sweeps=22,burn=2,m=2,seed=9)
        b=compare_sweeps(data,(22,),burn=2,chains=4,m=2,seed=9)
        self.assertEqual(a,b["checkpoints"][0])

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
