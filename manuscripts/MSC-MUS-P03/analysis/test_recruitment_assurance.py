import unittest
from recruitment_assurance import attainment, rounded_cap, pilot_lower, report


class RecruitmentAssuranceTests(unittest.TestCase):
    def test_historical_and_candidate(self):
        self.assertAlmostEqual(attainment(640,.7946660955),.813595,places=5)
        self.assertAlmostEqual(attainment(660,.7946660955),.991001,places=5)
        self.assertEqual(rounded_cap(.7946660955),660)
        self.assertEqual(rounded_cap(.75),700)
        self.assertEqual(rounded_cap(.70),760)

    def test_lower_uncertainty_and_no_authorization(self):
        self.assertAlmostEqual(pilot_lower(40,50),.6844039386)
        self.assertEqual(rounded_cap(pilot_lower(40,50)),780)
        self.assertFalse(report()["recruitment_authorized"])
        self.assertLess(attainment(660,.78),.95)

    def test_invalid_and_impossible(self):
        for p in (-1,1.1):
            with self.assertRaises(ValueError):
                attainment(660,p)
        with self.assertRaises(ValueError):
            pilot_lower(2,1)
        self.assertEqual(pilot_lower(0,30),0)
        self.assertIsNone(rounded_cap(.01,limit=800))
