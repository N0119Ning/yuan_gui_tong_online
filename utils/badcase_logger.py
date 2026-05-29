"""Badcase logger: record failed queries for iterative improvement."""

import json
import time
from pathlib import Path
from typing import Optional

LOG_PATH = Path(__file__).parent.parent / "data" / "badcases.jsonl"


def log_badcase(
    query: str,
    answer: str,
    results: list,
    issue: str,
    expected: Optional[str] = None,
):
    """Record a badcase entry.

    Args:
        query: user's question
        answer: LLM's response
        results: retrieved clauses (top 5)
        issue: what went wrong (e.g., 'hallucinated_clause', 'no_results', 'wrong_standard')
        expected: what the correct answer should be (optional)
    """
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "query": query,
        "issue": issue,
        "expected": expected or "",
        "answer": answer[:500],
        "retrieved": [
            {
                "standard": r.get("metadata", {}).get("standard_code", "?"),
                "clause": r.get("metadata", {}).get("clause_number", ""),
                "similarity": round(r.get("similarity", 0), 3),
                "content": r.get("content", "")[:200],
            }
            for r in (results or [])[:5]
        ],
    }

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"[Badcase] logged: {issue} — {query[:50]}")


def list_badcases() -> list:
    if not LOG_PATH.exists():
        return []
    entries = []
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries


def stats() -> dict:
    from collections import Counter
    entries = list_badcases()
    if not entries:
        return {"total": 0, "by_issue": {}}
    issues = Counter(e["issue"] for e in entries)
    return {"total": len(entries), "by_issue": dict(issues)}
