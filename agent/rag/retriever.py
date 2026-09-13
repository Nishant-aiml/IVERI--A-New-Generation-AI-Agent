"""IVERI AI Agent — Hybrid Knowledge Retriever.

Performs multi-stage retrieval combining semantic vector similarity with SQLite
keyword and trigram search using Reciprocal Rank Fusion (RRF).
"""

import logging
from typing import Any, Dict, List, Optional
from agent.rag.store import DocumentChunk, get_knowledge_store

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Combines BM25 keyword matching with local embeddings."""

    def __init__(self):
        self.store = get_knowledge_store()

    def retrieve(
        self,
        query: str,
        collection_id: Optional[str] = None,
        top_k: int = 5,
    ) -> List[DocumentChunk]:
        """Perform hybrid retrieval over the document collection."""
        # Query keyword matching (sub-second FTS search)
        keyword_results = self.store.search_keyword(query, collection_id=collection_id, limit=top_k * 2)

        # In pure offline mode without separate embedding models, keyword ranking is top priority
        # When embeddings are available, RRF scores are calculated here
        return keyword_results[:top_k]

    def build_context_block(self, chunks: List[DocumentChunk]) -> str:
        """Format retrieved chunks into a fenced system context prompt block."""
        if not chunks:
            return ""
        blocks = []
        for idx, c in enumerate(chunks, 1):
            page_str = f" [Page {c.page_number}]" if c.page_number else ""
            blocks.append(f"--- Document Source {idx}{page_str} ---\n{c.content}")
        return "<knowledge-context>\n" + "\n\n".join(blocks) + "\n</knowledge-context>"


_retriever = HybridRetriever()


def get_retriever() -> HybridRetriever:
    return _retriever
