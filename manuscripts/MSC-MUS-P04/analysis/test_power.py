import unittest
from power import power, required_n, report

class PowerTests(unittest.TestCase):
    def test_null(self):
        self.assertAlmostEqual(power(800, 0), .05, places=12)
    def test_symmetry(self):
        self.assertEqual(power(800,.2), power(800,-.2))
    def test_monotonicity(self):
        self.assertLess(power(480,.2), power(800,.2))
        self.assertLess(power(800,.15), power(800,.26))
    def test_target(self):
        for d in (.15,.20,.26,.30):
            n = required_n(d)
            self.assertGreaterEqual(power(n,d), .8)
            self.assertLess(power(n-1,d), .8)
    def test_protocol_scenarios(self):
        self.assertGreaterEqual(power(800,.2), .8)
        self.assertGreaterEqual(power(480,.26), .8)
        self.assertEqual(report()["status"], "DESIGN_ONLY")
    def test_validation(self):
        for n,d in ((0,.2),(800,float("nan"))):
            with self.assertRaises(ValueError):
                power(n,d)
        with self.assertRaises(ValueError):
            required_n(0)

if __name__ == "__main__":
    unittest.main()
