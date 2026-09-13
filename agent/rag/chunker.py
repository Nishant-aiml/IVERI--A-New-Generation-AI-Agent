"""IVERI AI Agent — Knowledge Chunker.

Breaks complex documents (scanned reports, 500-page manuals, codebases) into
semantically coherent chunks preserving section hierarchy and page numbers.
"""

import re
from typing import Any, Dict, List, Optional
from agent.rag.store import DocumentChunk
from tools.document_parsers.opendataloader_parser import ParsedDocument


class DocumentChunker:
    """Intelligent semantic chunker for RAG ingestion."""

    def __init__(self, target_chunk_size: int = 1000, overlap: int = 150):
        self.target_chunk_size = target_chunk_size
        self.overlap = overlap

    def chunk_parsed_document(
        self,
        doc: ParsedDocument,
        collection_id: str,
        document_id: str,
    ) -> List[DocumentChunk]:
        """Convert a ParsedDocument into an indexed list of DocumentChunks."""
        chunks: List[DocumentChunk] = []
        global_idx = 0

        for page in doc.pages:
            page_text = page.text.strip()
            if not page_text and not page.tables:
                continue

            # 1. Chunk text paragraphs
            paras = [p.strip() for p in page_text.split("\n\n") if p.strip()]
            current_buffer = ""

            for p in paras:
                if len(current_buffer) + len(p) <= self.target_chunk_size:
                    current_buffer += ("\n\n" if current_buffer else "") + p
                else:
                    if current_buffer:
                        chunks.append(
                            DocumentChunk(
                                chunk_id=f"{document_id}_c{global_idx}",
                                document_id=document_id,
                                collection_id=collection_id,
                                content=current_buffer,
                                chunk_index=global_idx,
                                page_number=page.page_number,
                                metadata={"type": "text", "page": page.page_number},
                            )
                        )
                        global_idx += 1
                    current_buffer = p

            if current_buffer:
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{document_id}_c{global_idx}",
                        document_id=document_id,
                        collection_id=collection_id,
                        content=current_buffer,
                        chunk_index=global_idx,
                        page_number=page.page_number,
                        metadata={"type": "text", "page": page.page_number},
                    )
                )
                global_idx += 1

            # 2. Add tables as distinct structured chunks to preserve tabular geometry
            for t_idx, tbl in enumerate(page.tables, 1):
                tbl_md = ParsedDocument._table_to_markdown(tbl)
                if tbl_md:
                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"{document_id}_tbl_{global_idx}",
                            document_id=document_id,
                            collection_id=collection_id,
                            content=f"### Table {t_idx} (Page {page.page_number})\n\n{tbl_md}",
                            chunk_index=global_idx,
                            page_number=page.page_number,
                            metadata={"type": "table", "page": page.page_number, "table_index": t_idx},
                        )
                    )
                    global_idx += 1

        return chunks


_chunker = DocumentChunker()


def get_chunker() -> DocumentChunker:
    return _chunker
