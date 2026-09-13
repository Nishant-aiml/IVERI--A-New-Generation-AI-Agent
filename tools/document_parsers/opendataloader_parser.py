"""IVERI AI Agent — OpenDataLoader PDF Parser.

High-fidelity layout-aware PDF parser capable of handling dense 500+ page documents:
- Extracts structured text, multi-column articles, and table geometries.
- Supports progressive page-range chunking (e.g. pages 1-25, 26-50) to prevent token window crashes.
- Emits clean Markdown tables and section hierarchies for downstream RAG indexing.
- Provides fallback to pypdf / pdfplumber if native OpenDataLoader is absent.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PDFPageExtract:
    """Extracted content from a single PDF page."""
    page_number: int
    text: str
    tables: List[List[List[str]]] = field(default_factory=list)  # list of 2D table matrices
    has_images: bool = False
    estimated_tokens: int = 0


@dataclass
class ParsedDocument:
    """Complete representation of a parsed document."""
    file_path: str
    total_pages: int
    title: Optional[str] = None
    pages: List[PDFPageExtract] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_markdown(self, start_page: int = 1, end_page: Optional[int] = None) -> str:
        """Render pages as structured Markdown with page boundaries."""
        end = end_page or self.total_pages
        blocks = []
        for p in self.pages:
            if start_page <= p.page_number <= end:
                blocks.append(f"<!-- Page {p.page_number} -->\n## Page {p.page_number}\n\n{p.text}")
                for idx, tbl in enumerate(p.tables, 1):
                    blocks.append(f"\n**Table {idx} (Page {p.page_number})**\n" + self._table_to_markdown(tbl))
        return "\n\n".join(blocks)

    @staticmethod
    def _table_to_markdown(table: List[List[str]]) -> str:
        if not table or not table[0]:
            return ""
        header = "| " + " | ".join(str(c).strip() for c in table[0]) + " |"
        sep = "| " + " | ".join("---" for _ in table[0]) + " |"
        rows = ["| " + " | ".join(str(c).strip() for c in row) + " |" for row in table[1:]]
        return "\n".join([header, sep] + rows)


class OpenDataLoaderPDFParser:
    """Layout-aware high-capacity PDF parsing engine."""

    def __init__(self):
        self._opendataloader_available = False
        try:
            import opendataloader_pdf  # type: ignore
            self._opendataloader_available = True
        except ImportError:
            self._opendataloader_available = False

    def is_native_available(self) -> bool:
        return self._opendataloader_available

    def parse_pdf(
        self,
        file_path: str | Path,
        start_page: int = 1,
        max_pages: Optional[int] = None,
    ) -> ParsedDocument:
        """Parse a PDF document with progressive streaming support for 500+ page files."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF document not found: {file_path}")

        # Native OpenDataLoader parsing path
        if self._opendataloader_available:
            try:
                return self._parse_with_opendataloader(path, start_page, max_pages)
            except Exception as e:
                logger.warning("OpenDataLoader failed, falling back to standard parser: %s", e)

        # Standard resilient fallback using bundled pdfplumber / pypdf
        return self._parse_with_fallback(path, start_page, max_pages)

    def _parse_with_opendataloader(
        self, path: Path, start_page: int, max_pages: Optional[int]
    ) -> ParsedDocument:
        import opendataloader_pdf  # type: ignore
        # Extract structured layout tree
        doc = opendataloader_pdf.load(str(path))
        pages: List[PDFPageExtract] = []
        total = len(doc.pages)
        limit = min(total, (start_page - 1) + (max_pages or total))

        for idx in range(start_page - 1, limit):
            p = doc.pages[idx]
            extracted_text = p.get_text() or ""
            tables = [t.extract() for t in p.find_tables()]
            pages.append(
                PDFPageExtract(
                    page_number=idx + 1,
                    text=extracted_text,
                    tables=tables,
                    has_images=bool(p.images),
                    estimated_tokens=len(extracted_text) // 4,
                )
            )

        return ParsedDocument(
            file_path=str(path),
            total_pages=total,
            pages=pages,
            metadata={"parser": "OpenDataLoader-PDF"},
        )

    def _parse_with_fallback(
        self, path: Path, start_page: int, max_pages: Optional[int]
    ) -> ParsedDocument:
        pages: List[PDFPageExtract] = []
        total_pages = 0

        # Try pdfplumber first (handles tables)
        try:
            import pdfplumber  # type: ignore
            with pdfplumber.open(path) as pdf:
                total_pages = len(pdf.pages)
                limit = min(total_pages, (start_page - 1) + (max_pages or total_pages))
                for idx in range(start_page - 1, limit):
                    p = pdf.pages[idx]
                    text = p.extract_text() or ""
                    tables = p.extract_tables() or []
                    clean_tables = [
                        [[str(cell or "").strip() for cell in row] for row in t if any(row)]
                        for t in tables if t
                    ]
                    pages.append(
                        PDFPageExtract(
                            page_number=idx + 1,
                            text=text,
                            tables=clean_tables,
                            has_images=bool(p.images),
                            estimated_tokens=len(text) // 4,
                        )
                    )
            return ParsedDocument(
                file_path=str(path),
                total_pages=total_pages,
                pages=pages,
                metadata={"parser": "pdfplumber-fallback"},
            )
        except ImportError:
            pass

        # Second fallback: pypdf
        try:
            import pypdf  # type: ignore
            reader = pypdf.PdfReader(str(path))
            total_pages = len(reader.pages)
            limit = min(total_pages, (start_page - 1) + (max_pages or total_pages))
            for idx in range(start_page - 1, limit):
                p = reader.pages[idx]
                text = p.extract_text() or ""
                pages.append(
                    PDFPageExtract(
                        page_number=idx + 1,
                        text=text,
                        estimated_tokens=len(text) // 4,
                    )
                )
            return ParsedDocument(
                file_path=str(path),
                total_pages=total_pages,
                pages=pages,
                metadata={"parser": "pypdf-fallback"},
            )
        except ImportError:
            pass

        # Raw extraction fallback
        return ParsedDocument(
            file_path=str(path),
            total_pages=1,
            pages=[PDFPageExtract(page_number=1, text="[Raw PDF text extraction unavailable - missing pdf parser]")],
            metadata={"parser": "none"},
        )


# Module-level singleton
_pdf_parser = OpenDataLoaderPDFParser()


def get_pdf_parser() -> OpenDataLoaderPDFParser:
    return _pdf_parser
