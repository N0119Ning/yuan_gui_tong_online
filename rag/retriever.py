"""Hybrid retriever: vector search (50%) + jieba keyword search (50%)."""

import numpy as np
import jieba
import chromadb
from typing import List, Optional


def _keyword_score(query: str, documents: List[str]) -> np.ndarray:
    query_tokens = set(jieba.cut(query))
    scores = np.zeros(len(documents))
    for i, doc in enumerate(documents):
        doc_tokens = set(jieba.cut(doc))
        if not query_tokens:
            continue
        scores[i] = len(query_tokens & doc_tokens) / len(query_tokens)
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

        # Get all documents for keyword scoring (or a larger batch)
        fetch_n = max(top_k * 4, 20)
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

        combined = 0.5 * vec_scores + 0.5 * kw_scores
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
