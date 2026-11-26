"""Known-variance planning for AIM-ER (synthetic design only)."""
import math
import random
from statistics import NormalDist

NORMAL = NormalDist()


def power(n, effect, cells=2, alpha=0.05, r2=0.0):
    if type(n) is not int or n < 2 or type(cells) is not int or cells not in (2, 4) or not 0 < alpha < 1:
        raise ValueError('invalid design')
    if not 0 <= r2 < 1 or not math.isfinite(effect):
        raise ValueError('invalid effect or R2')
    variance = (2 if cells == 2 else 1) * (1 - r2) / n
    shift = abs(effect) / math.sqrt(variance)
    critical = NORMAL.inv_cdf(1 - alpha / 2)
    return NORMAL.cdf(shift - critical) + NORMAL.cdf(-shift - critical)


def plan(effect, cells=2, target=0.8, alpha=0.05, r2=0.0, loss=0.15):
    if not 0 < alpha < target < 1 or not 0 <= loss < 1 or not effect > 0:
        raise ValueError('invalid target, loss or effect')
    hi = 2
    while power(hi, effect, cells, alpha, r2) < target:
        hi *= 2
        if hi > 10**8:
            raise ValueError('design exceeds planning bound')
    lo = 2
    while lo < hi:
        mid = (lo + hi) // 2
        if power(mid, effect, cells, alpha, r2) >= target:
            hi = mid
        else:
            lo = mid + 1
    return lo, cells * math.ceil(lo / (1 - loss))


def monte_carlo(n, effect, cells=2, reps=20000, seed=1729, alpha=0.05, r2=0.0):
    power(n, effect, cells, alpha, r2)
    if type(reps) is not int or reps < 1:
        raise ValueError('reps must be positive')
    rng = random.Random(seed)
    sd = math.sqrt((1 - r2) / n)
    weights = (-1, 1) if cells == 2 else (0.5, -0.5, -0.5, 0.5)
    means = (0, effect) if cells == 2 else (effect, 0, 0, effect)
    se = sd * math.sqrt(sum(w * w for w in weights))
    critical = NORMAL.inv_cdf(1 - alpha / 2)
    hits = 0
    for _ in range(reps):
        estimate = sum(w * rng.gauss(m, sd) for w, m in zip(weights, means))
        hits += abs(estimate / se) > critical
    return hits / reps


if __name__ == '__main__':
    for effect in (0.2, 0.3, 0.4, 0.5):
        print(effect, [plan(effect, k, r2=r)[1] for k in (2, 4) for r in (0, 0.25)])
    for cells in (2, 4):
        n, _ = plan(0.3, cells)
        print(cells, n, power(n, 0.3, cells), monte_carlo(n, 0.3, cells), monte_carlo(n, 0, cells))
