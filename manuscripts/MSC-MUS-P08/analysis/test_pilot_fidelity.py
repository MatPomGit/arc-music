import unittest
import numpy as np
from test_inference import fixture
from pilot_fidelity import pilot, equivalence, rate


def pilot_fixture():
    d=fixture()
    rng=np.random.default_rng(42)
    d["task_seconds"]=rng.normal(440,5,len(d))
    d["preview_seconds"]=rng.normal(180,5,len(d))
    for k in ("roles_correct","started_playback","playback_success"):
        d[k]=True
    return d


class PilotTests(unittest.TestCase):
    def test_exact_rates(self):
        self.assertEqual(rate(0,0)["ci"],None)
        self.assertEqual(rate(0,10)["ci"][0],0)
        self.assertEqual(rate(10,10)["ci"][1],1)

    def test_complete_comparisons(self):
        r=pilot(pilot_fixture(),10,10)
        self.assertEqual(r["randomised"],400)
        self.assertEqual(len(r["timing"]["task_seconds"]),6)
        self.assertTrue(r["joint_timing_equivalence"])

    def test_missing_is_not_equivalent(self):
        d=pilot_fixture()
        d.loc[0,"preview_seconds"]=np.nan
        r=pilot(d,10,10)
        self.assertFalse(r["joint_timing_equivalence"])
        self.assertEqual(r["cells"]["0/0"]["timing_missing"]["preview_seconds"],1)

    def test_unknown_flags_retained(self):
        d=pilot_fixture()
        d["roles_correct"]=d.roles_correct.astype("boolean")
        d.loc[0,"roles_correct"]=None
        r=pilot(d,10,10)["cells"]["0/0"]
        self.assertEqual(r["role_unknown"],1)
        self.assertEqual(r["role_comprehension"]["total"],100)
        self.assertEqual(r["role_comprehension"]["success"],99)

    def test_shift_and_degenerate(self):
        a=np.arange(100,dtype=float)
        self.assertEqual(equivalence(a,a+50,10)["status"],"not_established")
        self.assertEqual(equivalence([1,1],[1,1],10)["status"],"inconclusive")

    def test_impossible_exposure(self):
        d=pilot_fixture()
        d.loc[0,"preview_seconds"]=480
        with self.assertRaises(ValueError): pilot(d,10,10)

if __name__=="__main__": unittest.main()
