"""Synthetic identification examples for AIM-ER; no participant data."""
import argparse
import json
import math
import random
from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class Paths:
    a: float = 0.6
    b: float = 0.5
    c: float = 0.7
    direct: float = 0.1

    def equivalent(self, delta):
        return Paths(self.a, self.b + delta, self.c - delta,
                     self.direct - self.a * delta)

    def evaluate(self, z, u, e):
        m = self.a * z + u
        y = self.direct * z + self.b * m + self.c * u + e
        return m, y

    @property
    def total(self):
        return self.direct + self.a * self.b


def identification(n=2000, seed=1729):
    if n < 4 or n % 2:
        raise ValueError('n must be even and at least 4')
    rng = random.Random(seed)
    assignment = [0, 1] * (n // 2)
    rng.shuffle(assignment)
    p = Paths()
    q = p.equivalent(-0.5)
    groups = {0: [], 1: []}
    gap = 0.0
    for z in assignment:
        u, e = rng.gauss(0, 1), rng.gauss(0, 1)
        m, y = p.evaluate(z, u, e)
        m2, y2 = q.evaluate(z, u, e)
        gap = max(gap, abs(m - m2), abs(y - y2))
        groups[z].append(y)
    return {'n': n, 'total_effect': p.total,
            'estimated_total': mean(groups[1]) - mean(groups[0]),
            'indirect_a': p.a * p.b, 'indirect_b': q.a * q.b,
            'maximum_observed_difference': gap}


def factorial(n_per_cell=1000, seed=1730, match_effect=0.4):
    if n_per_cell < 2 or not math.isfinite(match_effect):
        raise ValueError('invalid factorial parameters')
    rng = random.Random(seed)
    cells = {}
    for g in (0, 1):
        for a in (0, 1):
            values = [0.2 * g - 0.1 * a + match_effect * (g == a)
                      + rng.gauss(0, 1) for _ in range(n_per_cell)]
            cells[g, a] = mean(values)
    contrast = (cells[0, 0] + cells[1, 1]
                - cells[0, 1] - cells[1, 0]) / 2
    return {'n_per_cell': n_per_cell, 'true_match_contrast': match_effect,
            'estimated_match_contrast': contrast}


def trajectories(relief=0.6, persistence=0.5, rumination_cost=0.8):
    if not all(map(math.isfinite, (relief, persistence, rumination_cost))):
        raise ValueError('parameters must be finite')
    if not 0 <= persistence <= 1 or rumination_cost < 0:
        raise ValueError('invalid persistence or cost')
    return {'immediate_relief': relief,
            'delayed_low_rumination': persistence * relief,
            'delayed_high_rumination': persistence * relief - rumination_cost}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=1729)
    args = parser.parse_args()
    print(json.dumps({'identification': identification(seed=args.seed),
                      'factorial': factorial(seed=args.seed + 1),
                      'trajectories': trajectories()}, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
