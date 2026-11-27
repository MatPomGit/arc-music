import unittest
import numpy as np
import pandas as pd
from inference import PREDICTORS
from simulation import draw
from sensitivity import sensitivity,weighted_within,cluster_bootstrap,interval_gate
from secondary import holm,secondary
from bounded_simulation import bounded

class TestExtensions(unittest.TestCase):
    def fixture(self):
        g,x,y=draw(np.random.default_rng(42),40,6,.3,missing=0)
        d=pd.DataFrame(x,columns=PREDICTORS)
        d["participant_id"]=g
        d["interference"]=np.clip(np.rint(y),0,10)
        d.loc[d.index%4==0,"interference"]=np.nan
        return d
    def test_sensitivity(self):
        r=sensitivity(self.fixture())
        self.assertEqual(len(r["pattern_mean_shifts"]),15)
        self.assertAlmostEqual(r["observation_rate"],.75)
        self.assertTrue(np.isfinite(list(r["ipw"].values())).all())
    def test_undefined_or_unknown_never_imputed(self):
        for state in ("undefined","unknown",None):
            d=self.fixture()
            d["endpoint_state"]="defined"
            d.loc[d.index[0],"endpoint_state"]=state
            with self.assertRaisesRegex(ValueError,"undefined or unknown"):
                sensitivity(d)
            with self.assertRaisesRegex(ValueError,"undefined or unknown"):
                cluster_bootstrap(d,reps=3)
    def test_bootstrap(self):
        r=cluster_bootstrap(self.fixture(),reps=5)
        self.assertEqual(r["valid"]+r["failed"],5)
        self.assertFalse(r["ci_reliable"])
        self.assertTrue(all(v is None for v in r["ipw_ci"].values()))
        self.assertTrue(all(v is None for v in r["shift_ci"].values()))
    def test_complete_outcomes_and_invalid_joint_draw(self):
        from unittest.mock import patch
        d=self.fixture()
        d["interference"]=d["interference"].fillna(5)
        r=sensitivity(d)
        self.assertEqual(r["observation_rate"],1.)
        self.assertEqual(r["min_probability"],1.)
        np.testing.assert_allclose(list(r["ipw"].values()),r["complete_case"],atol=1e-10)
        np.testing.assert_allclose(list(r["pattern_mean_shifts"].values()),r["complete_case"],atol=1e-10)
        invalid=dict(r,ipw={"10":float("nan"),"20":0.})
        with patch("sensitivity.sensitivity",side_effect=[r,invalid,r]):
            boot=cluster_bootstrap(d,reps=2)
        self.assertEqual((boot["valid"],boot["failed"]),(1,1))
        self.assertFalse(boot["ci_reliable"])
    def test_all_outer_failures_keep_all_methods(self):
        from unittest.mock import patch
        from bootstrap_calibration import run
        import json
        with patch("bootstrap_calibration.cluster_bootstrap",side_effect=ValueError("test failure")):
            out=run(reps=1,bootstrap=1,reference_n=100,n=40,seed=91)
        self.assertEqual(len(out["cells"]),6)
        for cell in out["cells"]:
            self.assertEqual(cell["point_failures"],1)
            self.assertEqual(len(cell["methods"]),17)
            self.assertEqual(cell["shift_envelope_available"],0)
            for m in cell["methods"].values():
                self.assertEqual(m["point_valid"],0)
                self.assertEqual(m["interval_unavailable"],1)
                self.assertEqual(m["coverage_operational"],0.)
                self.assertIsNone(m["bias"])
                self.assertIsNone(m["coverage_conditional"])
        json.dumps(out,allow_nan=False)
    def test_interval_gate(self):
        for count in (0,1,3,449):
            self.assertIsNone(interval_gate(list(range(count)),499))
        self.assertIsNone(interval_gate(list(range(498)),498))
        self.assertIsNotNone(interval_gate(list(range(450)),499))
        self.assertIsNotNone(interval_gate(list(range(499)),499))
    def test_holm(self):
        np.testing.assert_allclose(holm([.03,.01,.04]),[.06,.03,.06])
    def test_bounded(self):
        _,_,y=bounded(np.random.default_rng(4),80,6,.3)
        self.assertTrue(np.isin(y,np.arange(11)).all())
    def test_secondary(self):
        d=self.fixture().dropna().copy()
        rng=np.random.default_rng(3)
        d["distress_post"]=rng.integers(0,11,len(d))
        d["brooding"]=rng.integers(0,11,len(d))
        r=secondary(d)
        self.assertEqual(len(r),3)
        self.assertTrue(all(v["p_holm"]>=v["p"] for v in r))

    def test_secondary_preserves_family(self):
        d=self.fixture().dropna().copy()
        rng=np.random.default_rng(3)
        d["distress_post"]=rng.integers(0,11,len(d))
        r=secondary(d) # brooding absent
        self.assertTrue(r[0]["available"] and r[1]["available"])
        self.assertFalse(r[2]["available"])
        self.assertIsNone(r[2]["p_holm"])
        expected=holm([r[0]["p"],r[1]["p"],1.])
        np.testing.assert_allclose([r[0]["p_holm"],r[1]["p_holm"]],expected[:2])
        d["brooding"]=5 # rank-deficient
        r=secondary(d)
        self.assertTrue(r[0]["available"] and r[1]["available"])
        self.assertFalse(r[2]["available"])
        d["distress_post"]=np.nan
        self.assertTrue(all(not v["available"] for v in secondary(d)))
        d["brooding"]=11
        with self.assertRaises(ValueError): secondary(d)

if __name__=="__main__": unittest.main()
