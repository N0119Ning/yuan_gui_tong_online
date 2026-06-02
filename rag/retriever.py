"""Hybrid retriever: vector search + jieba keyword + bigram overlap."""

import re
import numpy as np
import jieba
import chromadb
from typing import List, Optional


def _keyword_score(query: str, documents: List[str]) -> np.ndarray:
    """Enhanced keyword scoring: substring match + token overlap + bigram bonus."""
    query_tokens = [t for t in jieba.cut(query) if len(t.strip()) > 1]
    # Generate query bigrams for fuzzy matching
    query_bigrams = set()
    query_clean = re.sub(r"[？?，。！!、]", "", query)
    for i in range(len(query_clean) - 1):
        query_bigrams.add(query_clean[i:i + 2])

    scores = np.zeros(len(documents))
    for i, doc in enumerate(documents):
        if not doc:
            continue
        doc_lower = doc.lower()
        # 1. Substring match: each query token found in doc
        tok_hits = sum(1 for t in query_tokens if t in doc_lower)
        tok_score = tok_hits / len(query_tokens) if query_tokens else 0

        # 2. Token intersection (Jaccard)
        doc_tokens = set(jieba.cut(doc))
        query_set = set(query_tokens)
        jaccard = len(query_set & doc_tokens) / len(query_set) if query_set else 0

        # 3. Bigram overlap (fuzzy match for OCR variants like "绿地率"/"録地率")
        doc_bigrams = set()
        doc_clean = re.sub(r"[^一-鿿]", "", doc_lower)
        for j in range(len(doc_clean) - 1):
            doc_bigrams.add(doc_clean[j:j + 2])
        bigram_overlap = len(query_bigrams & doc_bigrams) / len(query_bigrams) if query_bigrams else 0

        scores[i] = 0.35 * tok_score + 0.25 * jaccard + 0.40 * bigram_overlap

    return scores


def _normalize(scores: np.ndarray) -> np.ndarray:
    s_max, s_min = scores.max(), scores.min()
    if s_max == s_min:
        return np.zeros_like(scores)
    return (scores - s_min) / (s_max - s_min)


class HybridRetriever:
    def __init__(
        self,
        collection_name: str,
        persist_directory: str,
        embedder,
    ):
        self._client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedder.embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[dict] = None,
    ) -> List[dict]:
        where = filter_dict if filter_dict else None

        # Get more candidates for re-ranking (wider net = better recall)
        fetch_n = max(top_k * 16, 80)
        vec_results = self.collection.query(
            query_texts=[query],
            n_results=fetch_n,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        ids = vec_results["ids"][0]
        documents = vec_results["documents"][0]
        metadatas = vec_results["metadatas"][0]
        distances = np.array(vec_results["distances"][0])

        if not documents:
            return []

        vec_scores = 1 - _normalize(distances)
        kw_scores = _keyword_score(query, documents)

        # Balanced: vector for semantics, keyword for exact terms
        combined = 0.50 * vec_scores + 0.50 * kw_scores

        # Mild boost for mandatory standards (GB55014/GB55037/GB55019)
        # These are shorter standards that get out-voted by keyword-heavy old standards
        MANDATORY_BOOST = 1.12  # 12% boost for mandatory standards
        for i, meta in enumerate(metadatas):
            code = (meta or {}).get("standard_code", "")
            if code in ("GB55014", "GB55037", "GB55019"):
                combined[i] *= MANDATORY_BOOST

        ranked_idx = np.argsort(combined)[::-1][:top_k]

        results = []
        for idx in ranked_idx:
            results.append({
                "content": documents[idx],
                "metadata": metadatas[idx] or {},
                "similarity": float(combined[idx]),
            })
        return results

    def get_collection_stats(self) -> dict:
        count = self.collection.count()
        return {
            "collection_name": self.collection.name,
            "total_documents": count,
        }
