"""Conversation logger — Supabase REST API, no extra deps needed."""

import os
import json
import time
import urllib.request
import urllib.error


def _post(table: str, data: dict) -> bool:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        print("[Logger] Supabase not configured")
        return False

    req = urllib.request.Request(
        f"{url}/rest/v1/{table}",
        data=json.dumps(data).encode("utf-8"),
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req)
        return True
    except urllib.error.HTTPError as e:
        print(f"[Logger] Supabase error: {e.code} {e.read().decode()[:200]}")
        return False


def log(query: str, answer: str, results: list, invite_code: str = "", feedback: str = "", helpful: int = 0):
    retrieved_json = json.dumps([
        {
            "standard": r.get("metadata", {}).get("standard_code", ""),
            "clause": r.get("metadata", {}).get("clause_number", ""),
            "similarity": round(r.get("similarity", 0), 3),
        }
        for r in (results or [])[:5]
    ], ensure_ascii=False)

    ok = _post("conversations", {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "invite_code": invite_code,
        "query": query,
        "answer": answer[:2000],
        "retrieved": retrieved_json,
        "feedback": feedback,
        "helpful": helpful,
    })
    if not ok:
        print("[Logger] Failed to log conversation")


def get_daily_usage(code: str) -> int:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        return 0

    today = time.strftime("%Y-%m-%d")
    req = urllib.request.Request(
        f"{url}/rest/v1/conversations?select=id&invite_code=eq.{code}&timestamp=gte.{today}",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    try:
        resp = urllib.request.urlopen(req)
        rows = json.loads(resp.read().decode())
        return len(rows)
    except Exception:
        return 0
