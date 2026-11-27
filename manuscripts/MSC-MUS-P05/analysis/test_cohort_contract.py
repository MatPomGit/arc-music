"""Synthetic structural tests; no participant records."""
import unittest
from cohort_contract import audit_cohorts


def row(person, stage, episode="e1", lag=None):
    return dict(participant_code=person, episode_code=episode, stage=stage, lag_days=lag)


class CohortContractTests(unittest.TestCase):
    def test_independent_and_order_free(self):
        rows = [row("s3", "retest", lag=7), row("s1", "pilot"),
                row("s2", "efa"), row("s3", "cfa")]
        self.assertEqual(audit_cohorts(rows), dict(pilot=1, efa=1, cfa=1, retest=1))
        self.assertEqual(audit_cohorts([]), dict(pilot=0, efa=0, cfa=0, retest=0))

    def test_overlap_or_duplicate(self):
        for stage in ("pilot", "efa", "cfa"):
            with self.subTest(stage=stage), self.assertRaisesRegex(ValueError, "overlapping"):
                audit_cohorts([row("s1", "efa"), row("s1", stage)])

    def test_wrong_retest_parent(self):
        for rows in ([row("s1", "retest", lag=14)],
                     [row("s1", "efa"), row("s1", "retest", lag=14)],
                     [row("s1", "cfa"), row("s1", "retest", "e2", 14)]):
            with self.subTest(rows=rows), self.assertRaisesRegex(ValueError, "matching CFA"):
                audit_cohorts(rows)

    def test_retest_lag_and_duplicate(self):
        for lag in (6, 15, None, True, 7.0):
            with self.subTest(lag=lag), self.assertRaisesRegex(ValueError, "lag outside"):
                audit_cohorts([row("s1", "cfa"), row("s1", "retest", lag=lag)])
        with self.assertRaisesRegex(ValueError, "duplicate retest"):
            audit_cohorts([row("s1", "cfa"), row("s1", "retest", lag=7),
                           row("s1", "retest", lag=14)])
        self.assertEqual(audit_cohorts([row("s1", "cfa"), row("s1", "retest", lag=14)])["retest"], 1)

    def test_invalid_metadata(self):
        for item in (row("s1", "unknown"), row("s1", "pilot", lag=0),
                     row("", "efa"), dict(row("s1", "efa"), extra="synthetic")):
            with self.subTest(item=item), self.assertRaises(ValueError):
                audit_cohorts([item])

    def test_error_does_not_expose_codes(self):
        with self.assertRaises(ValueError) as err:
            audit_cohorts([row("synthetic_private", "retest", "synthetic_episode", 7)])
        self.assertNotIn("synthetic_private", str(err.exception))
        self.assertNotIn("synthetic_episode", str(err.exception))
