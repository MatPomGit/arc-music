"""Offline P09 transactional allocation prototype; not an approved service."""
import re
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from export_schema import VERSION, instant, validate_fields

def now():
    return datetime.now(timezone.utc).isoformat()

ID = re.compile(r"[0-9a-f]{32}")
DIGEST = re.compile(r"[0-9a-f]{64}")


def connect(path):
    db = sqlite3.connect(path, timeout=20, isolation_level=None)
    db.execute("PRAGMA foreign_keys=ON")
    return db


def initialise(db, bank_digest):
    db.execute("CREATE TABLE IF NOT EXISTS protocol (id INTEGER PRIMARY KEY CHECK(id=1), bank TEXT NOT NULL, version TEXT NOT NULL)")
    db.execute("INSERT OR IGNORE INTO protocol VALUES(1,?,?)", (bank_digest,VERSION))
    if db.execute("SELECT bank,version FROM protocol WHERE id=1").fetchone() != (bank_digest,VERSION):
        raise ValueError("Frozen bank mismatch")
    db.execute("""CREATE TABLE IF NOT EXISTS slots (
        id INTEGER PRIMARY KEY, training INTEGER NOT NULL CHECK(training IN (0,1)),
        music INTEGER NOT NULL CHECK(music IN (0,1)))""")
    db.execute("""CREATE TABLE IF NOT EXISTS assignments (
        participant_id TEXT PRIMARY KEY, slot INTEGER NOT NULL UNIQUE REFERENCES slots(id),
        randomised_at TEXT NOT NULL, withdrawn INTEGER NOT NULL DEFAULT 0 CHECK(withdrawn IN (0,1)), withdrawal_at TEXT)""")


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
                timestamp = now()
                db.execute("INSERT INTO assignments(participant_id,slot,randomised_at) VALUES(?,?,?)",
                           (participant_id,slot[0],timestamp))
                music = slot[1]
            db.commit()
            return dict(music=music, randomised_at=timestamp, bank_digest=bank_digest,schema_version=VERSION)
        except BaseException:
            db.rollback()
            raise


def withdraw(path, participant_id):
    """Cessation marker only; no claim that retention/deletion policy is approved."""
    validate_id(participant_id)
    with closing(connect(path)) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            found = db.execute("UPDATE assignments SET withdrawn=1,withdrawal_at=COALESCE(withdrawal_at,?) WHERE participant_id=?",
                               (now(),participant_id,)).rowcount
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


TERMINAL=("task_finished","task_stopped","task_technical_failure")

def record_checkpoint(path, participant_id, stage):
    """Atomic server-side timestamp and state transition; no browser flags.
    A repeated identical transition is idempotent while active.
    """
    validate_id(participant_id)
    if stage not in ("task_started",*TERMINAL,"t1_submitted","t2_submitted"):
        raise ValueError("Invalid checkpoint")
    with closing(connect(path)) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            active=db.execute("SELECT withdrawn,randomised_at FROM assignments WHERE participant_id=?",(participant_id,)).fetchone()
            if active is None or active[0]:
                raise ValueError("No active allocation")
            db.execute("""CREATE TABLE IF NOT EXISTS checkpoints (
                participant_id TEXT NOT NULL REFERENCES assignments(participant_id),
                stage TEXT NOT NULL, recorded_at TEXT NOT NULL,
                PRIMARY KEY(participant_id,stage))""")
            events=dict(db.execute("SELECT stage,recorded_at FROM checkpoints WHERE participant_id=?",(participant_id,)))
            if stage in events:
                db.commit();return events[stage]
            stamp=now();t=instant(stamp);assigned=instant(active[1])
            if t<assigned or any(t<instant(v) for v in events.values()):
                raise ValueError("Nonmonotonic event time")
            terminal=next((k for k in TERMINAL if k in events),None)
            elapsed=(t-assigned).total_seconds()
            if stage=="task_started":
                if events or elapsed>1800:
                    raise ValueError("Task start out of order or window")
            elif stage in TERMINAL:
                if "task_started" not in events or terminal or "t2_submitted" in events:
                    raise ValueError("Task terminal transition out of order")
                duration=(t-instant(events["task_started"])).total_seconds()
                if stage=="task_finished" and duration<480:
                    raise ValueError("Normal finish before task duration")
                if elapsed>1800:
                    raise ValueError("Task terminal outside immediate visit window")
            elif stage=="t1_submitted":
                if not terminal or elapsed>1800 or "t2_submitted" in events:
                    raise ValueError("T1 requires verified terminal event within immediate window")
            elif not 144*3600<=elapsed<=192*3600:
                raise ValueError("T2 outside independent follow-up window")
            db.execute("INSERT INTO checkpoints VALUES(?,?,?)",(participant_id,stage,stamp))
            db.commit();return stamp
        except BaseException:
            db.rollback();raise


def ledger(path):
    """Single read snapshot of consumed assignments and checkpoint events."""
    with closing(connect(path)) as db:
        db.execute("BEGIN")
        bank,version=db.execute("SELECT bank,version FROM protocol WHERE id=1").fetchone()
        if version!=VERSION:raise ValueError("Unsupported ledger schema")
        rows=db.execute("""SELECT a.participant_id,s.training,s.music,a.randomised_at,a.withdrawn
                  FROM assignments a JOIN slots s ON s.id=a.slot ORDER BY a.participant_id""").fetchall()
        exists=db.execute("SELECT name FROM sqlite_master WHERE name='checkpoints'").fetchone()
        events={}
        if exists:
            for pid,stage,stamp in db.execute("SELECT participant_id,stage,recorded_at FROM checkpoints"):
                events.setdefault(pid,{})[stage]=stamp
    result=[]
    for row in rows:
        rec=dict(zip(("participant_id","training","music","randomised_at","withdrawn"),row),
                 bank_digest=bank,schema_version=version)
        v=events.get(row[0],{})
        terminal=next((k for k in TERMINAL if k in v),None)
        rec.update(task_started_at=v.get("task_started"),task_ended_at=v.get(terminal),
                   task_end_reason=terminal,t1_at=v.get("t1_submitted"),t2_at=v.get("t2_submitted"))
        result.append(rec)
    return result


def reconcile(path,frame,*,strict=True):
    """Fail closed before analysis; strict=False is synthetic ledger-only testing."""
    import pandas as pd
    entries=ledger(path)
    if not entries:raise ValueError("Empty allocation ledger")
    if any(row["withdrawn"] for row in entries):
        raise ValueError("Withdrawal retention decision required before export")
    if strict:validate_fields(frame)
    required={"participant_id","training","music","randomised_at","bank_digest","schema_version"}
    if not required<=set(frame):raise ValueError("Missing ledger linkage fields")
    if frame.participant_id.duplicated().any() or set(frame.participant_id)!={e["participant_id"] for e in entries}:
        raise ValueError("Allocated cohort mismatch")
    observed=frame.set_index("participant_id")
    for e in entries:
        row=observed.loc[e["participant_id"]]
        for field in ("training","music","bank_digest","schema_version"):
            if pd.isna(row[field]) or row[field]!=e[field]:raise ValueError("Ledger mismatch: "+field)
        if instant(row.randomised_at)!=instant(e["randomised_at"]):raise ValueError("Ledger mismatch: randomised_at")
        if strict:
            for field in ("task_started_at","task_ended_at","t1_at","t2_at"):
                if instant(row[field])!=instant(e[field]):raise ValueError("Ledger mismatch: "+field)
            reason=None if pd.isna(row.task_end_reason) else row.task_end_reason
            if reason!=e["task_end_reason"]:raise ValueError("Ledger mismatch: task_end_reason")
    return len(entries)
