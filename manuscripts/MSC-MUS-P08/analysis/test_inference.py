import unittest
import numpy as np
import pandas as pd
from inference import analyze,prepare,holm
def fixture():
    rng=np.random.default_rng(42);rows=[]
    for a in [0,1]:
        for e in [0,1]:
            for i in range(100):
                r=dict(participant_id=f"{a}-{e}-{i}",authority=a,manual=e,training=int(rng.integers(2)),
                  prior_use_days=int(rng.integers(31)),familiarity=int(rng.integers(11)),
                  anticipated_ownership=int(rng.integers(11)),heard_version=True)
                for k,mu in [("ownership",4+1.2*a+.5*e+.8*a*e),("agency",4+1.4*a)]:
                    for j in range(1,4):r[k+str(j)]=int(np.clip(np.rint(mu+rng.normal(0,.8)),0,10))
                rows.append(r)
    return pd.DataFrame(rows)
class TestInference(unittest.TestCase):
    def test_factorial(self):
        r=analyze(fixture())
        self.assertAlmostEqual(r["hypotheses"]["H1"]["beta"],1.6,delta=.2)
        self.assertAlmostEqual(r["hypotheses"]["H3"]["beta"],.8,delta=.3)
        self.assertAlmostEqual(r["hypotheses"]["H2"]["beta"],1.4,delta=.2)
    def test_unheard_missing_not_zero(self):
        d=fixture();d.loc[0,"heard_version"]=False
        r=analyze(d);self.assertEqual(r["randomised"],400)
        self.assertEqual(r["cells"]["0/0"]["ownership_observed"],99)
        self.assertEqual(r["cells"]["0/0"]["unheard"],1)
        self.assertFalse(r["full_cohort_target_defined"])
        self.assertEqual(r["secondary_holm"],{"H2":None,"H3":None})
        for h in r["hypotheses"].values():
            self.assertFalse(h["confirmatory_available"])
            self.assertIn("descriptive_p",h)
            self.assertNotIn("p",h)
    def test_unknown_hearing_suppresses_confirmatory(self):
        d=fixture()
        d["heard_version"]=d.heard_version.astype("boolean")
        d.loc[0,"heard_version"]=pd.NA
        r=analyze(d)
        self.assertEqual(r["cells"]["0/0"]["hearing_unknown"],1)
        self.assertIsNone(r["secondary_holm"]["H2"])
        self.assertNotIn("ipw",r["missingness"]["ownership"])

    def test_defined_missing_preserves_confirmatory(self):
        d=fixture()
        d.loc[0,"ownership1"]=np.nan
        r=analyze(d)
        self.assertTrue(r["full_cohort_target_defined"])
        self.assertTrue(r["hypotheses"]["H1"]["confirmatory_available"])
        self.assertIn("p",r["hypotheses"]["H1"])
        self.assertIn("ipw",r["missingness"]["ownership"])

    def test_missing_item(self):
        d=fixture();d.loc[0,"ownership1"]=np.nan
        self.assertTrue(pd.isna(prepare(d).iloc[0].ownership))
        self.assertFalse(pd.isna(prepare(d).iloc[0].agency))
    def test_holm(self):
        self.assertEqual(holm({"H2":.03,"H3":None}),{"H2":.06,"H3":None})
    def test_missing_cell(self):
        d=fixture();d.loc[(d.authority==1)&(d.manual==1),"ownership1"]=np.nan
        r=analyze(d);self.assertIsNone(r["hypotheses"]["H1"])
        self.assertIsNotNone(r["hypotheses"]["H2"])
    def test_duplicate(self):
        d=fixture()
        with self.assertRaises(ValueError):prepare(pd.concat([d,d]))
if __name__=="__main__":unittest.main()
