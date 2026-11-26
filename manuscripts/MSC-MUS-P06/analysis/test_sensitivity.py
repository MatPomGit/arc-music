import unittest
import numpy as np
import pandas as pd
from inference import PREDICTORS
from simulation import draw
from sensitivity import sensitivity,weighted_within,cluster_bootstrap
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
    def test_bootstrap(self):
        r=cluster_bootstrap(self.fixture(),reps=5)
        self.assertEqual(r["valid"]+r["failed"],5)
        self.assertFalse(r["ci_reliable"])
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

if __name__=="__main__": unittest.main()
