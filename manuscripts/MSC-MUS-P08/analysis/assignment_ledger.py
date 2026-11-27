"""Versioned P08 offline assignment ledger. Restricted server use only.
Legacy allocation.py remains a historical synthetic helper. No deployment.
"""
import json
import re
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from allocation import CELLS
from task import system_choices
import pandas as pd

VERSION="p08-assignment-v1"
ID=re.compile(r"[0-9a-f]{32}")
DIGEST=re.compile(r"[0-9a-f]{64}")
FIELDS=("participant_id","training","authority","manual","randomised_at",
        "bank_digest","system_schedule","schema_version","withdrawn")

def connect(path):
    db=sqlite3.connect(path,timeout=20,isolation_level=None)
    db.execute("PRAGMA foreign_keys=ON")
    return db

def initialise(db,bank):
    db.execute("CREATE TABLE IF NOT EXISTS p08_protocol (id INTEGER PRIMARY KEY CHECK(id=1),bank TEXT NOT NULL,version TEXT NOT NULL)")
    db.execute("INSERT OR IGNORE INTO p08_protocol VALUES(1,?,?)",(bank,VERSION))
    if db.execute("SELECT bank,version FROM p08_protocol").fetchone()!=(bank,VERSION):
        raise ValueError("Frozen bank or schema mismatch")
    db.execute("CREATE TABLE IF NOT EXISTS p08_slots (id INTEGER PRIMARY KEY,training INTEGER NOT NULL,authority INTEGER NOT NULL,manual INTEGER NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS p08_schedules (id INTEGER PRIMARY KEY,authority INTEGER NOT NULL,manual INTEGER NOT NULL,sequence INTEGER NOT NULL)")
    db.execute("""CREATE TABLE IF NOT EXISTS p08_assignments (
      participant_id TEXT PRIMARY KEY,slot INTEGER UNIQUE NOT NULL REFERENCES p08_slots(id),
      schedule INTEGER UNIQUE NOT NULL REFERENCES p08_schedules(id),
      randomised_at TEXT NOT NULL,withdrawn INTEGER NOT NULL DEFAULT 0,
      withdrawal_at TEXT)""")

def validate_id(pid):
    if not isinstance(pid,str) or not ID.fullmatch(pid):raise ValueError("Invalid opaque identifier")

def allocate(path,pid,training,bank_digest,*,eligible,consented,baseline_complete,rng=None):
    validate_id(pid)
    if type(training) is not int or training not in (0,1):raise ValueError("Invalid training")
    if not isinstance(bank_digest,str) or not DIGEST.fullmatch(bank_digest):raise ValueError("Invalid bank digest")
    if not all(v is True for v in (eligible,consented,baseline_complete)):raise ValueError("Allocation gates not met")
    rng=secrets.SystemRandom() if rng is None else rng
    with closing(connect(path)) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            initialise(db,bank_digest)
            prior=db.execute("""SELECT s.training,s.authority,s.manual,q.sequence,a.randomised_at,a.withdrawn
                FROM p08_assignments a JOIN p08_slots s ON s.id=a.slot
                JOIN p08_schedules q ON q.id=a.schedule WHERE a.participant_id=?""",(pid,)).fetchone()
            if prior:
                if prior[5]:raise ValueError("Participant withdrawn")
                if prior[0]!=training:raise ValueError("Training stratum changed")
                _,authority,manual,sequence,stamp,_=prior
            else:
                query="SELECT id,authority,manual FROM p08_slots WHERE training=? AND id NOT IN (SELECT slot FROM p08_assignments) ORDER BY id LIMIT 1"
                slot=db.execute(query,(training,)).fetchone()
                if slot is None:
                    block=CELLS*rng.choice([1,2,3]);rng.shuffle(block)
                    db.executemany("INSERT INTO p08_slots(training,authority,manual) VALUES(?,?,?)",[(training,a,m) for a,m in block])
                    slot=db.execute(query,(training,)).fetchone()
                _,authority,manual=slot
                query2="SELECT id,sequence FROM p08_schedules WHERE authority=? AND manual=? AND id NOT IN (SELECT schedule FROM p08_assignments) ORDER BY id LIMIT 1"
                schedule=db.execute(query2,(authority,manual)).fetchone()
                if schedule is None:
                    order=list(range(16));rng.shuffle(order)
                    db.executemany("INSERT INTO p08_schedules(authority,manual,sequence) VALUES(?,?,?)",[(authority,manual,q) for q in order])
                    schedule=db.execute(query2,(authority,manual)).fetchone()
                sequence=schedule[1];stamp=datetime.now(timezone.utc).isoformat()
                db.execute("INSERT INTO p08_assignments(participant_id,slot,schedule,randomised_at) VALUES(?,?,?,?)",(pid,slot[0],schedule[0],stamp))
            db.commit()
            return dict(authority=authority,manual=manual,randomised_at=stamp,bank_digest=bank_digest,
                        system_schedule="".join(map(str,system_choices(sequence))),schema_version=VERSION)
        except BaseException:
            db.rollback();raise

def withdraw(path,pid):
    validate_id(pid)
    with closing(connect(path)) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            n=db.execute("UPDATE p08_assignments SET withdrawn=1,withdrawal_at=COALESCE(withdrawal_at,?) WHERE participant_id=?",
                (datetime.now(timezone.utc).isoformat(),pid)).rowcount
            if n!=1:raise ValueError("Unknown allocated participant")
            db.commit()
        except BaseException:
            db.rollback();raise

def ledger(path):
    with closing(connect(path)) as db:
        db.execute("BEGIN")
        bank,version=db.execute("SELECT bank,version FROM p08_protocol").fetchone()
        rows=db.execute("""SELECT a.participant_id,s.training,s.authority,s.manual,a.randomised_at,q.sequence,a.withdrawn
          FROM p08_assignments a JOIN p08_slots s ON s.id=a.slot
          JOIN p08_schedules q ON q.id=a.schedule ORDER BY a.participant_id""").fetchall()
    return [dict(participant_id=pid,training=t,authority=a,manual=m,randomised_at=stamp,
      bank_digest=bank,system_schedule="".join(map(str,system_choices(q))),schema_version=version,withdrawn=w)
      for pid,t,a,m,stamp,q,w in rows]

def reconcile(path,frame):
    entries=ledger(path)
    if not entries:raise ValueError("Empty ledger")
    if any(x["withdrawn"] for x in entries):raise ValueError("Approved withdrawal retention decision required")
    if not set(FIELDS[:-1])<=set(frame):raise ValueError("Missing assignment linkage fields")
    if frame.participant_id.duplicated().any() or set(frame.participant_id)!={x["participant_id"] for x in entries}:
        raise ValueError("Allocated cohort mismatch")
    observed=frame.set_index("participant_id")
    for x in entries:
        row=observed.loc[x["participant_id"]]
        for k in ("training","authority","manual","bank_digest","system_schedule","schema_version"):
            if pd.isna(row[k]) or row[k]!=x[k]:raise ValueError("Ledger mismatch: "+k)
        stamp=pd.Timestamp(row.randomised_at)
        if stamp.tzinfo is None or stamp!=pd.Timestamp(x["randomised_at"]):raise ValueError("Ledger mismatch: randomised_at")
    return len(entries)
