"""PDF parser: PyMuPDF for text-layer PDFs, PaddleOCR for scanned pages."""

import os
os.environ.setdefault("FLAGS_use_mkldnn", "0")

import re
from pathlib import Path
from typing import List

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

try:
    from paddleocr import PaddleOCR
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    PaddleOCR = None


class ParsedDocument:
    def __init__(self, standard_code: str, standard_name: str, full_markdown: str,
                 needs_ocr: bool = False, total_pages: int = 0, text_chars: int = 0):
        self.standard_code = standard_code
        self.standard_name = standard_name
        self.full_markdown = full_markdown
        self.needs_ocr = needs_ocr
        self.total_pages = total_pages
        self.text_chars = text_chars
        self.pages = self._split_by_headings()

    def _split_by_headings(self) -> List[dict]:
        sections = re.split(r"\n(?=## )", self.full_markdown)
        pages = []
        for i, section in enumerate(sections):
            if section.strip():
                pages.append({"page_num": i + 1, "text": section.strip()})
        return pages


def _parse_filename(filename: str) -> tuple:
    stem = Path(filename).stem
    parts = stem.split("_", 1)
    if len(parts) == 2:
        code_full, name = parts
        code = re.match(r"([A-Z]+\s*\d+)", code_full)
        return (code.group(1) if code else code_full, name)
    return (stem, "")


def _count_chinese(text: str) -> int:
    return len(re.findall(r"[一-鿿]", text))


def _clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\n\d{1,3}\n", "\n", text)
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append("")
            continue
        if result and result[-1] and not re.search(r"[。；：》\)”\\.!?]$", result[-1]):
            result[-1] += stripped
        else:
            result.append(stripped)
    return "\n".join(result)


def _resolve_path(p: str) -> Path:
    """Convert /e/... style bash paths to E:/... for Python on Windows."""
    path = Path(p)
    if not path.exists():
        # Try Windows drive letter conversion
        fixed = str(p).replace("/e/", "E:/").replace("/E/", "E:/")
        path = Path(fixed)
    return path


class PDFParser:
    def __init__(self, pdf_dir: str = "data/standards"):
        self.pdf_dir = _resolve_path(pdf_dir)
        self._ocr = None

    def _get_ocr(self):
        if not HAS_OCR:
            return None
        if self._ocr is None:
            self._ocr = PaddleOCR(use_angle_cls=True, lang="ch")
        return self._ocr

    def release_ocr(self):
        """Release PaddleOCR model to free memory (~1 GB)."""
        if self._ocr is not None:
            del self._ocr
            self._ocr = None
            import gc; gc.collect()

    def _extract_page(self, page, ocr) -> str:
        text = page.get_text().strip()
        if _count_chinese(text) >= 50:
            return text

        # Scanned page — render to image, run OCR
        pix = page.get_pixmap(dpi=200)
        img = pix.tobytes("png")
        result = ocr.ocr(img, cls=True)
        if not result or not result[0]:
            return ""

        lines = []
        for line_info in result[0]:
            if line_info and len(line_info) >= 2:
                text_part = line_info[1][0] if line_info[1] else ""
                if text_part.strip():
                    lines.append(text_part.strip())
        return "".join(lines)

    def parse_pdf(self, pdf_path: Path) -> ParsedDocument:
        code, name = _parse_filename(pdf_path.name)

        # Check OCR cache first — saves ~7 min per PDF on rebuild
        cache_dir = self.pdf_dir.parent / "ocr_cache"
        cache_dir.mkdir(exist_ok=True)
        cache_path = cache_dir / f"{pdf_path.stem}.txt"
        pdf_mtime = pdf_path.stat().st_mtime

        if cache_path.exists() and cache_path.stat().st_mtime > pdf_mtime:
            cached_text = cache_path.read_text(encoding="utf-8")
            total_chinese = _count_chinese(cached_text)
            avg = total_chinese / max(cached_text.count("## 第") or 1, 1)
            return ParsedDocument(code, name, cached_text,
                                  needs_ocr=(avg < 80),
                                  total_pages=cached_text.count("## 第"),
                                  text_chars=total_chinese)

        if not HAS_FITZ:
            raise RuntimeError("PyMuPDF not available. PDF parsing disabled in online mode.")
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        ocr = self._get_ocr()

        markdown_parts = [f"# {code} {name}\n"]
        total_chinese = 0

        for i, page in enumerate(doc):
            page_text = self._extract_page(page, ocr)
            total_chinese += _count_chinese(page_text)
            if page_text.strip():
                markdown_parts.append(f"## 第{i + 1}页\n\n{page_text.strip()}\n")

        doc.close()
        full_text = _clean_text("\n".join(markdown_parts))

        # Cache for future rebuilds
        cache_path.write_text(full_text, encoding="utf-8")

        avg_chars_per_page = total_chinese / max(total_pages, 1)
        needs_ocr = avg_chars_per_page < 80

        return ParsedDocument(code, name, full_text,
                              needs_ocr=needs_ocr, total_pages=total_pages,
                              text_chars=total_chinese)

    def parse_all(self, progress_callback=None) -> List[ParsedDocument]:
        docs = []
        pdfs = sorted(self.pdf_dir.glob("*.pdf"))
        total = len(pdfs)
        for i, pdf_file in enumerate(pdfs, 1):
            print(f"[{i}/{total}] Parsing: {pdf_file.name} ...")
            if progress_callback:
                progress_callback("parse", pdf_file.name, i, total)
            try:
                doc = self.parse_pdf(pdf_file)
                docs.append(doc)
                print(f"  -> {doc.standard_code}: {_count_chinese(doc.full_markdown)} chinese chars"
                      f"{' [需OCR]' if doc.needs_ocr else ''}")
            except Exception as e:
                print(f"  -> FAILED: {e}")
        return docs

    def get_low_text_pdfs(self) -> List[str]:
        """Return list of PDF filenames that may need OCR enhancement."""
        docs = self.parse_all()
        return [f"{d.standard_code}_{d.standard_name}.pdf" for d in docs if d.needs_ocr]
