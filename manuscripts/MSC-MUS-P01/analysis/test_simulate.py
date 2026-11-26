import math
import unittest
from simulate import Paths, identification, factorial, trajectories


class TestAIMER(unittest.TestCase):
    def test_equivalence(self):
        p = Paths()
        for delta in (-1.0, -0.5, 0.0, 0.7):
            q = p.equivalent(delta)
            self.assertAlmostEqual(p.total, q.total)
            for z in (0, 1):
                for u in (-2, 0, 3):
                    for e in (-1, 1):
                        for x, y in zip(p.evaluate(z, u, e), q.evaluate(z, u, e)):
                            self.assertAlmostEqual(x, y)

    def test_nonidentification(self):
        result = identification()
        self.assertAlmostEqual(result['indirect_a'], 0.3)
        self.assertAlmostEqual(result['indirect_b'], 0.0)
        self.assertLess(result['maximum_observed_difference'], 1e-12)
        self.assertLess(abs(result['estimated_total'] - result['total_effect']), 0.2)

    def test_factorial(self):
        self.assertAlmostEqual(factorial(match_effect=0.4)['estimated_match_contrast']
                               - factorial(match_effect=0.0)['estimated_match_contrast'], 0.4)
        self.assertLess(abs(factorial()['estimated_match_contrast'] - 0.4), 0.1)

    def test_delayed_reversal(self):
        r = trajectories()
        self.assertGreater(r['immediate_relief'], 0)
        self.assertGreater(r['delayed_low_rumination'], 0)
        self.assertLess(r['delayed_high_rumination'], 0)

    def test_trajectory_boundaries(self):
        self.assertAlmostEqual(trajectories(.6,1.,0.)['delayed_high_rumination'],.6)
        self.assertEqual(trajectories(.6,0.,0.)['delayed_high_rumination'],0.)
        self.assertAlmostEqual(trajectories(.6,.5,.3)['delayed_high_rumination'],0.)
        v=trajectories(.6,.5,0.)
        self.assertLess(v['delayed_high_rumination'],v['immediate_relief'])
        self.assertGreater(v['delayed_high_rumination'],0.)
        self.assertLess(trajectories(.6,.5,.8)['delayed_high_rumination'],0.)

    def test_reproducibility(self):
        self.assertEqual(identification(seed=5), identification(seed=5))
        self.assertEqual(factorial(seed=5), factorial(seed=5))

    def test_invalid_inputs(self):
        for fn, args in ((identification, (5,)), (factorial, (1,)),
                         (factorial, (2, 1, math.nan)),
                         (trajectories, (0.6, 1.1)),
                         (trajectories, (0.6, 0.5, -1))):
            with self.assertRaises(ValueError):
                fn(*args)


if __name__ == '__main__':
    unittest.main()
