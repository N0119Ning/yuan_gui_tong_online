"""Conversation logger — Supabase backend, survives redeploy."""

import os
import json
import time
from supabase import create_client


def _get_client():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        return None
    return create_client(url, key)


def log(query: str, answer: str, results: list, invite_code: str = "", feedback: str = "", helpful: int = 0):
    client = _get_client()
    if client is None:
        return

    retrieved_json = json.dumps([
        {
            "standard": r.get("metadata", {}).get("standard_code", ""),
            "clause": r.get("metadata", {}).get("clause_number", ""),
            "similarity": round(r.get("similarity", 0), 3),
        }
        for r in (results or [])[:5]
    ], ensure_ascii=False)

    client.table("conversations").insert({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "invite_code": invite_code,
        "query": query,
        "answer": answer[:2000],
        "retrieved": retrieved_json,
        "feedback": feedback,
        "helpful": helpful,
    }).execute()


def get_daily_usage(code: str) -> int:
    client = _get_client()
    if client is None:
        return 0
    today = time.strftime("%Y-%m-%d")
    try:
        r = client.table("conversations").select("id", count="exact").eq("invite_code", code).gte("timestamp", today).execute()
        return r.count or 0
    except Exception:
        return 0
