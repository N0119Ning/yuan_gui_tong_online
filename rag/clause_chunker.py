"""Clause chunker: parse OCR/extracted text into structured clauses."""

import re
from typing import List


class Clause:
    def __init__(self, page_content: str, metadata: dict):
        self.page_content = page_content
        self.metadata = metadata


# Match clause numbers anywhere in text (OCR output is continuous, no line breaks)
CLAUSE_BOUNDARY = re.compile(r"(第\d+(?:\.\d+)*条)")

# Match standalone numeric clause: 3.1.2, 6.0.3 — OCR text has no space after numbers
NUMERIC_CLAUSE = re.compile(r"(?:^|[。；\n])\s*(\d+(?:\.\d+)+)")

# Sub-clause: 1)、2）、(1)、(2) — used for splitting long clauses
SUB_CLAUSE = re.compile(r"(?:^|\n|[。；])\s*[\(（]?\d+[\)）][\.、]?\s")

MANDATORY_KEYWORDS = ["必须", "严禁", "应", "不应", "不得", "禁止"]

# Noise patterns: table of contents, staff lists, English-only, page footers
NOISE_PATTERNS = [
    re.compile(r"^[目][\s]*[次录]"),
    re.compile(r"^(浏览专用|住房城乡建设部|信息公[开升])"),
    re.compile(r"^[A-Za-z\s\d\.]+$"),  # English-only lines
    re.compile(r"^(高倩倩|范舒欣|刘晓嫣|朱祥明|黎茵|程梦倩|马怡馨|王威|李浩年|李平|姚睿|谢绮云|姜丛梅|李冠衡|宋岩|刘杰|朱志红|任荣志|赵鹏|莫长斌)"),  # Staff list
]


def _is_noise(text: str) -> bool:
    text = text.strip()
    if len(text) < 15:
        return False
    for pat in NOISE_PATTERNS:
        if pat.search(text):
            return True
    return False


def _is_mandatory(text: str) -> bool:
    return any(kw in text for kw in MANDATORY_KEYWORDS)


def _split_by_clause_boundaries(text: str) -> List[str]:
    """Split text at every clause boundary (第X.X条 or numeric heading)."""
    # Find all split points
    splits = []
    for pat in [CLAUSE_BOUNDARY, NUMERIC_CLAUSE]:
        for m in pat.finditer(text):
            pos = m.start()
            # For CLAUSE_BOUNDARY, the clause starts at 第
            if pat == CLAUSE_BOUNDARY:
                pos = m.start(1)
            splits.append(pos)

    if not splits:
        return [text] if text.strip() else []

    splits = sorted(set(splits))
    parts = []
    for i, pos in enumerate(splits):
        end = splits[i + 1] if i + 1 < len(splits) else len(text)
        part = text[pos:end].strip()
        if part:
            parts.append(part)

    # Also capture text before the first clause boundary
    if splits[0] > 0:
        prefix = text[:splits[0]].strip()
        if prefix and len(prefix) >= 20:
            parts.insert(0, prefix)

    return parts


def _merge_fragments(parts: List[str]) -> List[str]:
    """Merge short fragments (< 50 chars) into the next clause."""
    if len(parts) <= 1:
        return parts

    merged = []
    i = 0
    while i < len(parts):
        current = parts[i]
        # If this is a short fragment and there's a next clause, merge forward
        while len(current) < 50 and i + 1 < len(parts):
            i += 1
            current = current + parts[i]
        merged.append(current)
        i += 1
    return merged


def _clean_clause_text(text: str) -> str:
    """Remove page artifacts from clause text."""
    text = re.sub(r"浏览专用\s*\d*", "", text)
    text = re.sub(r"住房城乡建设部信息公[开升]", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = text.strip()
    return text


class ClauseChunker:
    def __init__(self, max_clause_chars: int = 4000):
        self.max_clause_chars = max_clause_chars

    def chunk_all(self, docs) -> List[Clause]:
        all_clauses = []
        for doc in docs:
            clauses = self._chunk_one(doc)
            all_clauses.extend(clauses)
        return all_clauses

    def _chunk_one(self, doc) -> List[Clause]:
        code = doc.standard_code
        name = doc.standard_name
        full_text = doc.full_markdown

        # Step 1: Remove markdown headings (page markers from PDF parsing)
        text = re.sub(r"^#.*$", "", full_text, flags=re.MULTILINE)
        text = re.sub(r"^## 第\d+页$", "", text, flags=re.MULTILINE)

        # Step 2: Split at clause boundaries
        raw_parts = _split_by_clause_boundaries(text)

        # Step 3: Merge short fragments
        merged_parts = _merge_fragments(raw_parts)

        # Step 4: Clean and filter
        clauses = []
        for part in merged_parts:
            part = _clean_clause_text(part)
            if not part or _is_noise(part):
                continue
            if len(part) < 15:
                continue

            clause_num = _detect_clause_number(part)
            heading = _detect_heading_context(part)

            # Split overly long clauses at sub-clause boundaries
            sub_parts = _split_long(part, self.max_clause_chars)
            for sp in sub_parts:
                clauses.append(Clause(sp, {
                    "standard_code": code,
                    "standard_name": name,
                    "clause_number": clause_num or "",
                    "heading": heading or "",
                    "is_mandatory": _is_mandatory(sp),
                }))

        return clauses


def _detect_clause_number(text: str) -> str | None:
    m = CLAUSE_BOUNDARY.search(text)
    if m:
        return m.group(1).replace("第", "").replace("条", "")
    m = NUMERIC_CLAUSE.search(text)
    if m:
        return m.group(1)
    return None


def _detect_heading_context(text: str) -> str | None:
    """Extract section heading context if present."""
    m = re.match(r"^([\d\.]+\s*\S.{0,30})\s", text)
    if m:
        return m.group(1).strip()
    m = re.match(r"^(第[一二三四五六七八九十百]+[章节篇])", text)
    if m:
        return m.group(1)
    return None


def _split_long(text: str, max_chars: int) -> List[str]:
    if len(text) <= max_chars:
        return [text]

    # Try to split at sub-clause markers or paragraph breaks
    parts = []
    current = ""
    for segment in re.split(r"(\n\n|(?<=\s)\d+[\)）])", text):
        if len(current) + len(segment) > max_chars and current.strip():
            parts.append(current.strip())
            current = segment
        else:
            current += segment
    if current.strip():
        parts.append(current.strip())
    return parts if parts else [text]
