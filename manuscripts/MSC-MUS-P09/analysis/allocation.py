"""Offline P09 transactional allocation prototype; not an approved service."""
import re
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

ID = re.compile(r"[0-9a-f]{32}")
DIGEST = re.compile(r"[0-9a-f]{64}")


def connect(path):
    db = sqlite3.connect(path, timeout=20, isolation_level=None)
    db.execute("PRAGMA foreign_keys=ON")
    return db


def initialise(db, bank_digest):
    db.execute("CREATE TABLE IF NOT EXISTS protocol (id INTEGER PRIMARY KEY CHECK(id=1), bank TEXT NOT NULL)")
    db.execute("INSERT OR IGNORE INTO protocol VALUES(1,?)", (bank_digest,))
    if db.execute("SELECT bank FROM protocol WHERE id=1").fetchone()[0] != bank_digest:
        raise ValueError("Frozen bank mismatch")
    db.execute("""CREATE TABLE IF NOT EXISTS slots (
        id INTEGER PRIMARY KEY, training INTEGER NOT NULL CHECK(training IN (0,1)),
        music INTEGER NOT NULL CHECK(music IN (0,1)))""")
    db.execute("""CREATE TABLE IF NOT EXISTS assignments (
        participant_id TEXT PRIMARY KEY, slot INTEGER NOT NULL UNIQUE REFERENCES slots(id),
        randomised_at TEXT NOT NULL, withdrawn INTEGER NOT NULL DEFAULT 0 CHECK(withdrawn IN (0,1)))""")


def validate_id(participant_id):
    if not isinstance(participant_id, str) or not ID.fullmatch(participant_id):
        raise ValueError("Expected server-generated opaque 128-bit identifier")


def allocate(path, participant_id, training, bank_digest, *, eligible, consented,
             baseline_complete, rng=None):
    """Caller must authenticate and verify all gates server-side; never trust browser flags."""
    validate_id(participant_id)
    if type(training) is not int or training not in (0,1):
        raise ValueError("Invalid training")
    if not isinstance(bank_digest, str) or not DIGEST.fullmatch(bank_digest):
        raise ValueError("Invalid bank digest")
    if not all(v is True for v in (eligible, consented, baseline_complete)):
        raise ValueError("Allocation gates not met")
    rng = secrets.SystemRandom() if rng is None else rng
    with closing(connect(path)) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            initialise(db, bank_digest)
            prior = db.execute("""SELECT s.training,s.music,a.randomised_at,a.withdrawn
                FROM assignments a JOIN slots s ON s.id=a.slot WHERE a.participant_id=?""",
                (participant_id,)).fetchone()
            if prior:
                if prior[3]:
                    raise ValueError("Participant withdrawn")
                if prior[0] != training:
                    raise ValueError("Training stratum changed")
                music, timestamp = prior[1:3]
            else:
                query = """SELECT id,music FROM slots WHERE training=? AND id NOT IN
                    (SELECT slot FROM assignments) ORDER BY id LIMIT 1"""
                slot = db.execute(query, (training,)).fetchone()
                if slot is None:
                    block = [0,1] * rng.choice((2,3))
                    rng.shuffle(block)
                    db.executemany("INSERT INTO slots(training,music) VALUES(?,?)",
                                   [(training, arm) for arm in block])
                    slot = db.execute(query,(training,)).fetchone()
                timestamp = datetime.now(timezone.utc).isoformat()
                db.execute("INSERT INTO assignments(participant_id,slot,randomised_at) VALUES(?,?,?)",
                           (participant_id,slot[0],timestamp))
                music = slot[1]
            db.commit()
            return dict(music=music, randomised_at=timestamp, bank_digest=bank_digest)
        except BaseException:
            db.rollback()
            raise


def withdraw(path, participant_id):
    """Cessation marker only; no claim that retention/deletion policy is approved."""
    validate_id(participant_id)
    with closing(connect(path)) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            found = db.execute("UPDATE assignments SET withdrawn=1 WHERE participant_id=?",
                               (participant_id,)).rowcount
            if found != 1:
                raise ValueError("Unknown allocated participant")
            db.commit()
        except BaseException:
            db.rollback()
            raise


def assert_active(path, participant_id):
    validate_id(participant_id)
    with closing(connect(path)) as db:
        found = db.execute("SELECT withdrawn FROM assignments WHERE participant_id=?",
                           (participant_id,)).fetchone()
    if found != (0,):
        raise ValueError("No active allocation")


def record_checkpoint(path, participant_id, stage):
    """Persist only a minimal synthetic/offline stage marker while consent is active.

    The check and write share the withdrawal transaction lock. No network
    effects or personal content are accepted by this prototype.
    """
    validate_id(participant_id)
    if stage not in ("task_started", "task_finished", "t1_submitted", "t2_submitted"):
        raise ValueError("Invalid checkpoint")
    with closing(connect(path)) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            active = db.execute("SELECT withdrawn FROM assignments WHERE participant_id=?",
                                (participant_id,)).fetchone()
            if active != (0,):
                raise ValueError("No active allocation")
            db.execute("""CREATE TABLE IF NOT EXISTS checkpoints (
                participant_id TEXT NOT NULL REFERENCES assignments(participant_id),
                stage TEXT NOT NULL, recorded_at TEXT NOT NULL,
                PRIMARY KEY(participant_id,stage))""")
            db.execute("INSERT OR IGNORE INTO checkpoints VALUES(?,?,?)",
                       (participant_id, stage, datetime.now(timezone.utc).isoformat()))
            db.commit()
        except BaseException:
            db.rollback()
            raise


def ledger(path):
    """Restricted analyst/server use only: consumed assignments, never future slots."""
    with closing(connect(path)) as db:
        bank = db.execute("SELECT bank FROM protocol WHERE id=1").fetchone()[0]
        rows = db.execute("""SELECT a.participant_id,s.training,s.music,a.randomised_at,a.withdrawn
                  FROM assignments a JOIN slots s ON s.id=a.slot ORDER BY a.participant_id""").fetchall()
    return [dict(zip(("participant_id","training","music","randomised_at","withdrawn"),row),
                 bank_digest=bank) for row in rows]


def reconcile(path, frame):
    """Fail closed on omitted/extra allocations, altered assignment, or cessation.

    For withdrawal an approved retention decision is needed before analysis export.
    """
    import pandas as pd
    entries = ledger(path)
    if not entries:
        raise ValueError("Empty allocation ledger")
    if any(row["withdrawn"] for row in entries):
        raise ValueError("Withdrawal retention decision required before export")
    required = {"participant_id","training","music","randomised_at","bank_digest"}
    if not required <= set(frame):
        raise ValueError("Missing ledger linkage fields")
    if frame.participant_id.duplicated().any() or set(frame.participant_id) != {e["participant_id"] for e in entries}:
        raise ValueError("Allocated cohort mismatch")
    observed = frame.set_index("participant_id")
    for e in entries:
        row = observed.loc[e["participant_id"]]
        for field in ("training","music","bank_digest"):
            if pd.isna(row[field]) or row[field] != e[field]:
                raise ValueError("Ledger mismatch: "+field)
        recorded = pd.Timestamp(row.randomised_at)
        if recorded.tzinfo is None or recorded != pd.Timestamp(e["randomised_at"]):
            raise ValueError("Ledger mismatch: randomised_at")
    return len(entries)
