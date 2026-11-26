import unittest
import numpy as np
from secondary import secondary,holm
from simulation import generate
from calibration import robustness,run_scenario
from inference import impute_pmm,target_weights,pooled_contrast

class SecondaryTests(unittest.TestCase):
    def test_holm(self):
        np.testing.assert_allclose(holm([.04,.01]),[.04,.02])
        np.testing.assert_allclose(holm([.03,.04]),[.06,.06])
        with self.assertRaises(ValueError):
            holm([np.nan,.5])
    def test_secondary(self):
        rng=np.random.default_rng(42)
        x,y,_=generate(240,.4,"mar",rng)
        f=x[:,2]+rng.normal(size=len(x))
        f[:10]=np.nan
        out=secondary(x[:,1]+.5,x[:,2],f,x[:,4:],y,m=4)
        self.assertEqual(out["H2"]["excluded_missing_ndif"],10)
        self.assertEqual(out["H3"]["n_baseline_eligible"],240)
        self.assertEqual(len(out["H2"]["sensitivity"]),27)
        for h in ("H2","H3"):
            v=out[h]
            self.assertGreaterEqual(v["holm_p"],v["mar"]["p"])
            zero=[s for s in v["sensitivity"] if s["offset_control"]==s["offset_scaffold"]==s["differential_slope"]==0][0]
            self.assertAlmostEqual(zero["estimate"],v["mar"]["estimate"])
    def test_robust_implies_nominal(self):
        x,y,_=generate(240,0,"mar",np.random.default_rng(2))
        d=impute_pmm(x,y,4,1); w=target_weights(x)
        q=pooled_contrast(x,d,w)
        if robustness(x,y,d,w,q):
            self.assertLess(q["p"],.05)
    def test_smoke(self):
        s=run_scenario(240,.6,"mar",3,3,7)
        self.assertEqual(s["valid"],3)
        self.assertEqual(s["failed"],0)
        self.assertLessEqual(s["grid_robust_rejection"],s["nominal_rejection"])

if __name__=="__main__":
    unittest.main()
