"""SQLite storage: documents, chunks, mastery + attempt log. No server needed."""
from __future__ import annotations
import sqlite3
import time
from pathlib import Path
from .config import db_path, ensure_dirs

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
  doc_id TEXT PRIMARY KEY,
  path TEXT UNIQUE,
  filename TEXT,
  ftype TEXT,
  hash TEXT,
  indexed_at REAL,
  chunk_count INTEGER DEFAULT 0,
  status TEXT DEFAULT 'ok'
);
CREATE TABLE IF NOT EXISTS chunks (
  chunk_id TEXT PRIMARY KEY,
  doc_id TEXT,
  filename TEXT,
  path TEXT,
  page TEXT,
  section TEXT,
  text TEXT
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
CREATE TABLE IF NOT EXISTS mastery (
  concept TEXT PRIMARY KEY,
  state TEXT DEFAULT 'UNKNOWN',
  attempts INTEGER DEFAULT 0,
  correct INTEGER DEFAULT 0,
  incorrect INTEGER DEFAULT 0,
  streak INTEGER DEFAULT 0,
  ever_failed INTEGER DEFAULT 0,
  updated REAL
);
CREATE TABLE IF NOT EXISTS strategies (
  concept TEXT PRIMARY KEY,
  used TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  concept TEXT DEFAULT '',
  verdict TEXT DEFAULT '',
  ts REAL
);
CREATE INDEX IF NOT EXISTS idx_attempts_ts ON attempts(ts);
"""

def connect(db: Path | None = None) -> sqlite3.Connection:
    ensure_dirs()
    p = db or db_path()
    con = sqlite3.connect(str(p))
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con

def doc_count(con: sqlite3.Connection) -> int:
    return con.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"]

def chunk_count(con: sqlite3.Connection) -> int:
    return con.execute("SELECT COUNT(*) c FROM chunks").fetchone()["c"]

def list_documents(con: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in con.execute(
        "SELECT path, filename, ftype, chunk_count, datetime(indexed_at,'unixepoch','localtime') AS indexed FROM documents ORDER BY filename"
    ).fetchall()]

def remove_document(con: sqlite3.Connection, name_or_path: str) -> int:
    """Remove by filename or full path. Returns chunks deleted."""
    row = con.execute("SELECT doc_id FROM documents WHERE path=? OR filename=? OR doc_id=?",
                      (name_or_path, name_or_path, name_or_path)).fetchone()
    if row is None:
        # fuzzy: match substring of filename
        rows = con.execute("SELECT doc_id, filename FROM documents").fetchall()
        hits = [r for r in rows if name_or_path.lower() in r["filename"].lower()]
        if len(hits) == 1:
            row = hits[0]
        elif len(hits) > 1:
            names = ", ".join(h["filename"] for h in hits)
            raise RuntimeError(f"Multiple matches: {names}. Be more specific.")
        else:
            raise RuntimeError(f"Document not found: `{name_or_path}`. Run `mindloop sources` to list.")
    doc_id = row["doc_id"]
    n = con.execute("SELECT COUNT(*) c FROM chunks WHERE doc_id=?", (doc_id,)).fetchone()["c"]
    con.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
    con.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
    con.commit()
    return n

def log_attempt(con: sqlite3.Connection, concept: str, verdict: str) -> None:
    try:
        con.execute("INSERT INTO attempts(concept, verdict, ts) VALUES(?,?,?)",
                    (concept, verdict, time.time()))
        con.commit()
    except Exception:
        pass


def recent_attempts(con: sqlite3.Connection, limit: int = 20) -> list[dict]:
    try:
        rows = con.execute(
            "SELECT concept, verdict, datetime(ts,'unixepoch','localtime') AS at FROM attempts ORDER BY id DESC LIMIT ?",
            (limit,)).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def attempts_per_day(con: sqlite3.Connection, days: int = 28) -> list[int]:
    """Counts per day, oldest first, for heatmap."""
    try:
        rows = con.execute(
            "SELECT date(ts,'unixepoch','localtime') AS d, COUNT(*) c FROM attempts "
            "WHERE ts > ? GROUP BY d",
            (time.time() - days * 86400,)).fetchall()
        m = {r["d"]: r["c"] for r in rows}
        import datetime as _dt
        today = _dt.date.today()
        out = []
        for i in range(days - 1, -1, -1):
            d = (today - _dt.timedelta(days=i)).isoformat()
            out.append(int(m.get(d, 0)))
        return out
    except Exception:
        return []


def upsert_mastery(con: sqlite3.Connection, concept: str, **kw) -> None:
    row = con.execute("SELECT * FROM mastery WHERE concept=?", (concept,)).fetchone()
    if row is None:
        con.execute(
            "INSERT INTO mastery(concept,state,attempts,correct,incorrect,streak,ever_failed,updated) VALUES(?,?,?,?,?,?,?,?)",
            (concept, kw.get("state", "UNKNOWN"), kw.get("attempts", 0), kw.get("correct", 0),
             kw.get("incorrect", 0), kw.get("streak", 0), 1 if kw.get("ever_failed") else 0, time.time()),
        )
    else:
        fields = []
        vals = []
        for k in ("state", "attempts", "correct", "incorrect", "streak", "ever_failed"):
            if k in kw:
                v = kw[k]
                if k == "ever_failed":
                    v = 1 if v else 0
                fields.append(f"{k}=?")
                vals.append(v)
        fields.append("updated=?")
        vals.append(time.time())
        vals.append(concept)
        con.execute(f"UPDATE mastery SET {', '.join(fields)} WHERE concept=?", vals)
    con.commit()
