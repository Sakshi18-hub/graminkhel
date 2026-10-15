"""SQLite storage (auto-adds new columns to an existing database)."""
import sqlite3, pandas as pd

DB = "graminkhel.db"
NEW_COLS = {"broad_cm": "REAL", "shuttle_s": "REAL", "run_min": "REAL",
            "flags": "TEXT", "id_checked": "INTEGER DEFAULT 0"}

def conn():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS athletes(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, age INTEGER,
        gender TEXT, village TEXT, district TEXT, sport TEXT, height_cm REAL,
        jump_cm REAL, sprint_s REAL, score REAL, percentile REAL,
        verify_code TEXT, verified INTEGER DEFAULT 0,
        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    have = {r[1] for r in c.execute("PRAGMA table_info(athletes)")}
    for k, v in NEW_COLS.items():
        if k not in have:
            c.execute(f"ALTER TABLE athletes ADD COLUMN {k} {v}")
    c.commit()
    return c

def add_athlete(**r):
    c = conn()
    cols = ",".join(r); q = ",".join("?" * len(r))
    c.execute(f"INSERT INTO athletes({cols}) VALUES({q})", list(r.values()))
    c.commit(); c.close()

def all_athletes():
    c = conn(); df = pd.read_sql("SELECT * FROM athletes", c); c.close()
    return df

def set_verified(aid, v=1):
    c = conn(); c.execute("UPDATE athletes SET verified=? WHERE id=?", (v, aid))
    c.commit(); c.close()
