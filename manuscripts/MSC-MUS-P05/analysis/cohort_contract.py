"""Prospective P05 cohort checks; no collection or scoring authorization.

Use only synthetic fixtures or authorized restricted processing. Stage names
are local roles, not registry dataset IDs. A shared, opaque participant code
must be supplied by an approved linkage procedure; this cannot detect aliases.
Errors contain row numbers, never participant or episode codes.
"""
import re

STAGES = ("pilot", "efa", "cfa", "retest")
FIELDS = {"participant_code", "episode_code", "stage", "lag_days"}
CODE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def audit_cohorts(rows):
    """Return structural counts or reject inconsistent records without dropping any.

    lag_days is elapsed time from CFA to retest, null otherwise. This checks
    supplied metadata only; it does not verify consent, dates or identity.
    """
    baseline = {}
    retests = {}
    counts = dict.fromkeys(STAGES, 0)
    for i, row in enumerate(rows, 1):
        def fail(reason):
            raise ValueError(f"row {i}: {reason}")

        if not isinstance(row, dict) or set(row) != FIELDS:
            fail("unexpected fields")
        person, episode = row["participant_code"], row["episode_code"]
        if any(not isinstance(v, str) or not CODE.fullmatch(v) for v in (person, episode)):
            fail("invalid opaque code")
        stage, lag = row["stage"], row["lag_days"]
        if stage not in STAGES:
            fail("unknown stage")
        if stage == "retest":
            if type(lag) is not int or not 7 <= lag <= 14:
                fail("retest lag outside 7 to 14 days")
            if person in retests:
                fail("duplicate retest")
            retests[person] = (episode, i)
        else:
            if lag is not None:
                fail("baseline lag must be null")
            if person in baseline:
                fail("duplicate baseline or overlapping cohorts")
            baseline[person] = (stage, episode)
        counts[stage] += 1
    for person, (episode, i) in retests.items():
        if baseline.get(person) != ("cfa", episode):
            raise ValueError(f"row {i}: retest requires matching CFA person and episode")
    return counts
