"""Transactional allocation prototype. Deploy only behind an approved server.

Never expose database, upcoming slots or random generator to participants.
Default randomness is OS-backed; seeded RNG injection is for synthetic tests only.
"""
import sqlite3
import secrets
from contextlib import closing

CELLS=[(0,0),(0,1),(1,0),(1,1)]
def allocate(path,participant_id,training,rng=None):
    if not isinstance(participant_id,str) or not participant_id.strip():raise ValueError("Invalid participant ID")
    if type(training) is not int or training not in (0,1):raise ValueError("Invalid training stratum")
    rng=secrets.SystemRandom() if rng is None else rng
    with closing(sqlite3.connect(path,timeout=20,isolation_level=None)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute("CREATE TABLE IF NOT EXISTS slots (id INTEGER PRIMARY KEY, training INTEGER NOT NULL CHECK(training IN (0,1)), authority INTEGER NOT NULL CHECK(authority IN (0,1)), manual INTEGER NOT NULL CHECK(manual IN (0,1)))")
            db.execute("CREATE TABLE IF NOT EXISTS assignments (participant_id TEXT PRIMARY KEY, slot INTEGER NOT NULL UNIQUE REFERENCES slots(id), allocated_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')))")
            prior=db.execute("SELECT s.training,s.authority,s.manual FROM assignments a JOIN slots s ON s.id=a.slot WHERE a.participant_id=?",(participant_id,)).fetchone()
            if prior is not None:
                if prior[0]!=training:raise ValueError("Training stratum changed after allocation")
                db.commit()
                return {"authority":prior[1],"manual":prior[2]}
            query="SELECT id,authority,manual FROM slots WHERE training=? AND id NOT IN (SELECT slot FROM assignments) ORDER BY id LIMIT 1"
            slot=db.execute(query,(training,)).fetchone()
            if slot is None:
                block=CELLS*rng.choice([1,2,3])
                rng.shuffle(block)
                db.executemany("INSERT INTO slots(training,authority,manual) VALUES(?,?,?)",[(training,a,e) for a,e in block])
                slot=db.execute(query,(training,)).fetchone()
            db.execute("INSERT INTO assignments(participant_id,slot) VALUES(?,?)",(participant_id,slot[0]))
            db.commit()
            return {"authority":slot[1],"manual":slot[2]}
        except BaseException:
            db.rollback()
            raise
