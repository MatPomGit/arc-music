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
