import unittest
from power import power, plan, monte_carlo


class PowerTests(unittest.TestCase):
    def test_null(self):
        for cells in (2, 4):
            self.assertAlmostEqual(power(100, 0, cells), 0.05)

    def test_minimal_n(self):
        for cells in (2, 4):
            for effect in (0.2, 0.3, 0.5):
                n, _ = plan(effect, cells)
                self.assertGreaterEqual(power(n, effect, cells), 0.8)
                self.assertLess(power(n - 1, effect, cells), 0.8)

    def test_scaling(self):
        self.assertAlmostEqual(power(100, 0.3, 2), power(50, 0.3, 4))
        self.assertGreater(power(100, 0.3, r2=0.25), power(100, 0.3))

    def test_loss(self):
        self.assertGreater(plan(0.3, loss=0.15)[1], plan(0.3, loss=0)[1])

    def test_mc(self):
        for cells in (2, 4):
            for effect in (0, 0.3):
                self.assertLess(abs(monte_carlo(100, effect, cells) - power(100, effect, cells)), 0.015)

    def test_table_and_parameters(self):
        expected = ((926, 696, 928, 700), (412, 310, 416, 312),
                    (234, 176, 236, 176), (150, 114, 152, 116))
        for effect, row in zip((.2,.3,.4,.5), expected):
            self.assertEqual(tuple(plan(effect,k,r2=r)[1] for k in (2,4) for r in (0,.25)), row)
            for k in (2,4):
                for r in (0,.25):
                    n,_ = plan(effect,k,r2=r)
                    self.assertGreaterEqual(power(n,effect,k,r2=r),.8)
                    self.assertLess(power(n-1,effect,k,r2=r),.8)
        for k in (2,4):
            for effect in (0.,-.3,.3):
                expected = power(100,effect,k,alpha=.1,r2=.25)
                mc = monte_carlo(100,effect,k,alpha=.1,r2=.25)
                self.assertLess(abs(mc-expected),5*(expected*(1-expected)/20000)**.5)
            self.assertAlmostEqual(power(100,-.3,k),power(100,.3,k))
        for args in ((2.5,.3),(10,.3,2.0),(True,.3)):
            with self.assertRaises(ValueError):
                power(*args)
        with self.assertRaises(ValueError):
            monte_carlo(10,.3,reps=2.5)

    def test_invalid(self):
        for args in ((1, 0.3), (10, 0.3, 3), (10, float('nan'))):
            with self.assertRaises(ValueError):
                power(*args)
        with self.assertRaises(ValueError):
            plan(0)


if __name__ == '__main__':
    unittest.main()
