import unittest
import numpy as np
from validity import domain_score,effect,bootstrap_test,holm,validity_family

class ValidityTests(unittest.TestCase):
    def test_scoring(self):
        x=[[0,1,2,3,np.nan],[0,1,2,np.nan,np.nan]]
        with self.assertRaises(ValueError):
            domain_score(x)
        scores=domain_score(x,authorized=True)
        self.assertEqual(scores[0],1.5)
        self.assertTrue(np.isnan(scores[1]))
    def test_rank_effects(self):
        x=np.arange(100)
        self.assertAlmostEqual(effect(np.column_stack([x,x**2]),"spearman"),1)
        rng=np.random.default_rng(42)
        z=rng.normal(size=1000); a=z+rng.normal(size=1000); b=z+rng.normal(size=1000)
        data=np.column_stack([a,b,z])
        self.assertLess(abs(effect(data,"partial")),.1)
        self.assertGreater(effect(data[:,:2],"spearman"),.3)
    def test_holm(self):
        np.testing.assert_allclose(holm([.03,.001,1,.02]),[.06,.004,1,.06])
    def test_paired_complete(self):
        rng=np.random.default_rng(1)
        x=rng.normal(size=150); y=x+rng.normal(size=150); z=rng.normal(size=150)
        z[:20]=np.nan
        out=bootstrap_test([x,y,z],"paired_difference",reps=99)
        self.assertEqual(out["n"],130)
        self.assertGreater(out["estimate"],.4)
    def test_unavailable_slots(self):
        x=np.arange(100.)
        out=validity_family({"EXP":x},{"expression":x},authorized=True,reps=99)
        self.assertEqual(len(out),6)
        self.assertEqual(out["H5_EXP_specificity"]["holm_p"],1.)
        self.assertTrue(out["H3_EXP_expression"]["supports_directional_hypothesis"])
        with self.assertRaises(ValueError):
            validity_family({},{})

if __name__=="__main__":
    unittest.main()
