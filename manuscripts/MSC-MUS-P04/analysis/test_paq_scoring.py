import unittest
import numpy as np
from paq_scoring import score,validate_items,describe_scores,FACETS,COMPOSITES

class PAQScoringTests(unittest.TestCase):
    def test_partition(self):
        self.assertEqual(sorted(i for indices in FACETS.values() for i in indices),list(range(1,25)))
        self.assertEqual(len(COMPOSITES),6)
    def test_bounds(self):
        s=score(np.array([[1]*24,[7]*24]))
        for f in ("nddf","ndif","pddf","pdif"):
            np.testing.assert_array_equal(s[f],[4,28])
        np.testing.assert_array_equal(s["geot"],[8,56])
        np.testing.assert_array_equal(s["ndaf"],[8,56])
        np.testing.assert_array_equal(s["gdaf"],[16,112])
        np.testing.assert_array_equal(s["total"],[24,168])
    def test_item_mapping(self):
        x=np.ones((1,24))
        x[0,np.array([1,7,13,19])-1]=7
        x[0,np.array([2,8,14,20])-1]=4
        s=score(x)
        self.assertEqual(s["nddf"][0],28)
        self.assertEqual(s["ndif"][0],16)
        self.assertEqual(s["ndaf"][0],44)
        self.assertEqual(s["total"][0],60)
    def test_missing_not_prorated(self):
        x=np.ones((3,24))
        x[0,1]=np.nan
        x[1,0]=np.nan
        x[2,2]=np.nan
        s=score(x)
        np.testing.assert_array_equal(s["h1_h3_baseline_eligible"],[True,False,True])
        np.testing.assert_array_equal(s["h2_common_baseline_eligible"],[False,False,True])
        self.assertTrue(np.isnan(s["ndaf"][:2]).all())
        self.assertTrue(np.isnan(s["total"]).all())
        self.assertEqual(s["nddf"][0],4)
    def test_invalid_inputs(self):
        for v in (0,8,2.5,np.inf):
            x=np.ones((1,24)); x[0,0]=v
            with self.assertRaises(ValueError):
                validate_items(x)
        for x in (np.ones(24),np.ones((2,23)),np.full((1,24),"1"),np.ones((1,24),bool)):
            with self.assertRaises(ValueError):
                validate_items(x)
    def test_describe(self):
        out=describe_scores([4,28,16,np.nan],4,28)
        self.assertEqual(out["n_observed"],3)
        self.assertEqual(out["n_missing"],1)
        self.assertAlmostEqual(out["floor_fraction"],1/3)
        self.assertAlmostEqual(out["ceiling_fraction"],1/3)
        self.assertIsNone(describe_scores([np.nan],4,28)["mean"])
        with self.assertRaises(ValueError):
            describe_scores([29],4,28)

if __name__=="__main__":
    unittest.main()
