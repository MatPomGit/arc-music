import unittest
from planning import candidate_domain_mean, correlation_sample_size

class PlanningTests(unittest.TestCase):
    def test_sample(self):
        self.assertEqual(correlation_sample_size(.2), 194)
        self.assertGreater(correlation_sample_size(.15), correlation_sample_size(.2))
        self.assertGreater(correlation_sample_size(.2, .90), correlation_sample_size(.2))
    def test_invalid(self):
        for r in (0, 1, -1):
            with self.assertRaises(ValueError):
                correlation_sample_size(r)
    def test_scoring_guard(self):
        with self.assertRaises(ValueError):
            candidate_domain_mean([0,1,2,3,4])
    def test_missing_is_not_zero(self):
        self.assertEqual(candidate_domain_mean([0,1,2,3,None], validated=True), 1.5)
        self.assertIsNone(candidate_domain_mean([0,1,2,None,None], validated=True))
        self.assertEqual(candidate_domain_mean([0,0,0], validated=True), 0)
    def test_invalid_response(self):
        for bad in (True, 5, -1, 1.5, float("nan")):
            with self.assertRaises(ValueError):
                candidate_domain_mean([0,1,bad], validated=True)
