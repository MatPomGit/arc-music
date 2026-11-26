import unittest
import numpy as np
from paq_scoring import score,validate_items,validate_total,describe_scores

class PAQSScoringTests(unittest.TestCase):
    def test_bounds(self):
        np.testing.assert_array_equal(score([[1]*6,[7]*6])["total"],[6,42])
    def test_sum(self):
        np.testing.assert_array_equal(score([[1,2,3,4,5,6]])["total"],[21])
    def test_missing(self):
        x=np.ones((2,6)); x[0,2]=np.nan
        out=score(x)
        np.testing.assert_array_equal(out["paq_baseline_eligible"],[False,True])
        self.assertTrue(np.isnan(out["total"][0]))
        self.assertEqual(set(out),{"total","paq_baseline_eligible"})
    def test_invalid_items(self):
        for v in (0,8,2.5,np.inf):
            x=np.ones((1,6)); x[0,0]=v
            with self.assertRaises(ValueError): validate_items(x)
        for x in (np.ones(6),np.ones((2,24)),np.ones((2,5)),np.full((1,6),"1"),np.ones((1,6),bool)):
            with self.assertRaises(ValueError): validate_items(x)
    def test_invalid_total(self):
        for v in (5,43,12.5,np.nan,np.inf):
            with self.assertRaises(ValueError): validate_total([v])
    def test_describe(self):
        out=describe_scores([6,42,24,np.nan])
        self.assertEqual(out["n_observed"],3)
        self.assertEqual(out["n_missing"],1)
        self.assertAlmostEqual(out["floor_fraction"],1/3)
        self.assertAlmostEqual(out["ceiling_fraction"],1/3)
        self.assertIsNone(describe_scores([np.nan])["mean"])
