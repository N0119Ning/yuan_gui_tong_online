"""Knowledge base: orchestrates PDF parsing → clause chunking → embedding → storage."""

import os
import gc
from pathlib import Path
from typing import List, Optional
from collections import defaultdict

from .embedder import EmbeddingManager  # torch must load before paddle
from .retriever import HybridRetriever
from .pdf_parser import PDFParser, ParsedDocument
from .clause_chunker import ClauseChunker


CHROMA_BATCH = 32

# Resolve absolute default paths relative to this module
_MODULE_DIR = Path(__file__).resolve().parent.parent


def _parse_filename_static(filename: str) -> tuple:
    """Parse standard code from filename without needing PDFParser."""
    import re
    stem = Path(filename).stem
    parts = stem.split("_", 1)
    if len(parts) == 2:
        code = re.match(r"([A-Z]+\s*\d+)", parts[0])
        return (code.group(1) if code else parts[0], parts[1])
    return (stem, "")


def _abs(path: str) -> str:
    p = Path(path)
    if p.is_absolute():
        return str(p)
    return str(_MODULE_DIR / p)


class KnowledgeBase:
    def __init__(
        self,
        collection_name: str = "ygt_v2",
        persist_directory: str = "./data/chroma_db",
        pdf_dir: str = "./data/standards",
    ):
        self.collection_name = collection_name
        persist_directory = _abs(persist_directory)
        pdf_dir = _abs(pdf_dir)
        self.persist_directory = persist_directory
        self.pdf_dir = pdf_dir

        os.makedirs(persist_directory, exist_ok=True)

        self.embedder = EmbeddingManager()
        self.retriever = HybridRetriever(
            collection_name=collection_name,
            persist_directory=persist_directory,
            embedder=self.embedder,
        )
        self.parser = PDFParser(pdf_dir=pdf_dir)
        self.chunker = ClauseChunker()
        self.low_text_pdfs = []

    @property
    def collection(self):
        return self.retriever.collection

    def build(self, pdf_dir: Optional[str] = None, progress_callback=None, force: bool = False):
        if pdf_dir:
            self.pdf_dir = _abs(pdf_dir)
            self.parser = PDFParser(pdf_dir=self.pdf_dir)

        # Get already-indexed standards
        existing_standards = set()
        if self.collection.count() > 0:
            all_meta = self.collection.get(include=["metadatas"])
            existing_standards = {
                m.get("standard_code", "")
                for m in (all_meta.get("metadatas") or [])
                if m and m.get("standard_code")
            }

        pdfs = sorted(self.parser.pdf_dir.glob("*.pdf"))
        # Filter: only process PDFs whose standard codes are NOT yet in the DB
        new_pdfs = []
        for pdf_file in pdfs:
            code, _ = _parse_filename_static(pdf_file.name)
            if code not in existing_standards:
                new_pdfs.append(pdf_file)

        if not new_pdfs:
            existing_count = self.collection.count()
            print(f"[KnowledgeBase] 所有 {len(pdfs)} 份规范已入库 ({existing_count} 条)，跳过构建")
            if progress_callback:
                progress_callback("done", f"已是最新 ({existing_count} 条)", existing_count, existing_count)
            return

        print(f"[KnowledgeBase] 已入库: {len(existing_standards)} 份, 新增: {len(new_pdfs)} 份")
        total_pdfs = len(new_pdfs)

        self.low_text_pdfs = []
        total_clauses = 0
        clause_counter = self.collection.count()

        for pdf_idx, pdf_file in enumerate(new_pdfs, 1):
            if progress_callback:
                progress_callback("parse", pdf_file.name, pdf_idx, total_pdfs)

            # --- Parse one PDF ---
            try:
                doc = self.parser.parse_pdf(pdf_file)
            except Exception as e:
                print(f"[{pdf_idx}/{total_pdfs}] FAILED: {pdf_file.name} — {e}")
                continue

            if doc.needs_ocr:
                self.low_text_pdfs.append(f"{doc.standard_code} {doc.standard_name}")

            # --- Chunk one doc ---
            clauses = self.chunker._chunk_one(doc)

            # --- Build lists for this doc only ---
            ids, texts, metadatas = [], [], []
            for clause in clauses:
                ids.append(f"clause_{clause_counter:06d}")
                texts.append(clause.page_content)
                metadatas.append(clause.metadata)
                clause_counter += 1

            # --- Upsert in small batches ---
            for start in range(0, len(texts), CHROMA_BATCH):
                end = min(start + CHROMA_BATCH, len(texts))
                self.collection.upsert(
                    ids=ids[start:end],
                    documents=texts[start:end],
                    metadatas=metadatas[start:end],
                )
                if progress_callback:
                    progress_callback(
                        "embed",
                        f"{pdf_file.name} ({pdf_idx}/{total_pdfs})",
                        pdf_idx,
                        total_pdfs,
                    )

            total_clauses += len(clauses)
            del doc, clauses, ids, texts, metadatas
            gc.collect()

        # --- Release OCR model ---
        self.parser.release_ocr()

        if progress_callback:
            progress_callback("done", "知识库构建完成", total_clauses, total_clauses)

        print(f"[KnowledgeBase] 构建完成：{total_clauses} 条条款已入库")
        if self.low_text_pdfs:
            names = ", ".join(self.low_text_pdfs)
            print(f"[KnowledgeBase] 注意：以下规范文本较少: {names}")

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        return self.retriever.retrieve(query, top_k=top_k)

    def get_stats(self) -> dict:
        all_data = self.collection.get(include=["metadatas"])
        metadatas = all_data.get("metadatas", [])

        total = len(metadatas)
        mandatory_count = sum(1 for m in metadatas if m.get("is_mandatory"))

        standards = defaultdict(int)
        for m in metadatas:
            code = m.get("standard_code", "未知")
            standards[code] += 1

        return {
            "total_clauses": total,
            "mandatory_count": mandatory_count,
            "standards": dict(sorted(standards.items())),
        }

    def clear(self):
        try:
            self.retriever._client.delete_collection(name=self.collection_name)
        except ValueError:
            pass
        self.retriever.collection = self.retriever._client.create_collection(
            name=self.collection_name,
            embedding_function=self.embedder.embedding_function,
            metadata={"hnsw:space": "cosine"},
        )
        print(f"[KnowledgeBase] 已清空集合: {self.collection_name}")
