"""Conversation logger: SQLite-based, auto-creates table."""

import sqlite3
import json
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "conversations.db"


def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            invite_code TEXT DEFAULT '',
            query TEXT NOT NULL,
            answer TEXT NOT NULL,
            retrieved TEXT,
            feedback TEXT,
            helpful INTEGER
        )
    """)
    # Add invite_code column if upgrading existing DB
    try:
        conn.execute("ALTER TABLE conversations ADD COLUMN invite_code TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    return conn


def log(query: str, answer: str, results: list, invite_code: str = "", feedback: str = "", helpful: int = 0):
    conn = _get_conn()
    retrieved_json = json.dumps([
        {
            "standard": r.get("metadata", {}).get("standard_code", ""),
            "clause": r.get("metadata", {}).get("clause_number", ""),
            "similarity": round(r.get("similarity", 0), 3),
        }
        for r in (results or [])[:5]
    ], ensure_ascii=False)

    conn.execute(
        "INSERT INTO conversations (timestamp, invite_code, query, answer, retrieved, feedback, helpful) VALUES (?,?,?,?,?,?,?)",
        (time.strftime("%Y-%m-%d %H:%M:%S"), invite_code, query, answer[:2000], retrieved_json, feedback, helpful),
    )
    conn.commit()
    conn.close()


def stats():
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    today = conn.execute(
        "SELECT COUNT(*) FROM conversations WHERE date(timestamp)=date('now','localtime')"
    ).fetchone()[0]
    feedbacks = conn.execute(
        "SELECT feedback, COUNT(*) FROM conversations WHERE feedback!='' GROUP BY feedback ORDER BY COUNT(*) DESC"
    ).fetchall()
    conn.close()
    return {"total": total, "today": today, "by_feedback": dict(feedbacks)}
