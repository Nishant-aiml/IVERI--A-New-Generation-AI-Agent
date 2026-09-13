"""IVERI AI Agent — Knowledge Fabric Store.

Embedded local storage for RAG collections, document records, and vector embeddings.
Uses the central SQLite `state.db` database under `$IVERI_HOME/state.db`.
"""

import json
import logging
import os
import sqlite3
import struct
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """A semantic chunk of an indexed document."""
    chunk_id: str
    document_id: str
    collection_id: str
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class KnowledgeStore:
    """Manages collections, document references, and chunk storage."""

    def __init__(self, db_path: Optional[Path] = None):
        from hermes_constants import get_hermes_home
        self.db_path = db_path or (get_hermes_home() / "state.db")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        """Create RAG tables if not already initialized."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS rag_collections (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rag_documents (
                    id TEXT PRIMARY KEY,
                    collection_id TEXT NOT NULL REFERENCES rag_collections(id) ON DELETE CASCADE,
                    path TEXT NOT NULL,
                    doc_hash TEXT NOT NULL,
                    mtime REAL NOT NULL,
                    chunk_count INTEGER DEFAULT 0,
                    created_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
                    collection_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    page_number INTEGER,
                    content TEXT NOT NULL,
                    embedding BLOB,
                    metadata_json TEXT,
                    created_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_rag_chunks_coll ON rag_chunks(collection_id);
                CREATE INDEX IF NOT EXISTS idx_rag_chunks_doc ON rag_chunks(document_id);
            """)

    def create_collection(self, name: str, description: str = "") -> str:
        """Create or get a collection by name."""
        cid = name.lower().replace(" ", "_")
        now = time.time()
        with self._get_connection() as conn:
            try:
                conn.execute(
                    "INSERT INTO rag_collections (id, name, description, created_at) VALUES (?, ?, ?, ?)",
                    (cid, name, description, now),
                )
                return cid
            except sqlite3.IntegrityError:
                row = conn.execute("SELECT id FROM rag_collections WHERE name = ? OR id = ?", (name, cid)).fetchone()
                return row["id"] if row else cid

    def register_document(self, document_id: str, collection_id: str, path: str, doc_hash: str = "hash", chunk_count: int = 0) -> str:
        """Register or update a document in rag_documents."""
        actual_coll_id = self.create_collection(collection_id)  # Guarantee collection exists & get PK
        now = time.time()
        with self._get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO rag_documents 
                   (id, collection_id, path, doc_hash, mtime, chunk_count, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (document_id, actual_coll_id, path, doc_hash, now, chunk_count, now),
            )
        return document_id

    def insert_chunks(self, chunks: List[DocumentChunk]) -> int:
        """Batch insert document chunks (ensures parent doc exists)."""
        # Ensure all unique parent documents and collections are registered
        coll_map = {}
        docs_seen = set()
        for c in chunks:
            if c.collection_id not in coll_map:
                coll_map[c.collection_id] = self.create_collection(c.collection_id)
            actual_coll = coll_map[c.collection_id]
            if (c.document_id, actual_coll) not in docs_seen:
                self.register_document(c.document_id, actual_coll, path=c.document_id)
                docs_seen.add((c.document_id, actual_coll))

        records = []
        now = time.time()
        for c in chunks:
            actual_coll = coll_map[c.collection_id]
            c.collection_id = actual_coll

            emb_bytes = None
            if c.embedding:
                # Pack float list into binary BLOB
                emb_bytes = struct.pack(f"{len(c.embedding)}f", *c.embedding)
            records.append(
                (
                    c.chunk_id,
                    c.document_id,
                    actual_coll,
                    c.chunk_index,

                    c.page_number,
                    c.content,
                    emb_bytes,
                    json.dumps(c.metadata),
                    now,
                )
            )


        with self._get_connection() as conn:
            conn.executemany(
                """INSERT OR REPLACE INTO rag_chunks 
                   (id, document_id, collection_id, chunk_index, page_number, content, embedding, metadata_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                records,
            )
        return len(records)

    def search_keyword(self, query: str, collection_id: Optional[str] = None, limit: int = 5) -> List[DocumentChunk]:
        """Perform sub-second keyword search over chunks."""
        terms = [t for t in query.split() if len(t) > 2]
        if not terms:
            return []
        like_pattern = "%" + "%".join(terms) + "%"

        sql = "SELECT * FROM rag_chunks WHERE content LIKE ?"
        params = [like_pattern]
        if collection_id:
            sql += " AND collection_id = ?"
            params.append(collection_id)
        sql += " LIMIT ?"
        params.append(limit)

        chunks: List[DocumentChunk] = []
        with self._get_connection() as conn:
            for row in conn.execute(sql, params):
                chunks.append(
                    DocumentChunk(
                        chunk_id=row["id"],
                        document_id=row["document_id"],
                        collection_id=row["collection_id"],
                        content=row["content"],
                        chunk_index=row["chunk_index"],
                        page_number=row["page_number"],
                        metadata=json.loads(row["metadata_json"] or "{}"),
                    )
                )
        return chunks


# Singleton instance
_knowledge_store = KnowledgeStore()


def get_knowledge_store() -> KnowledgeStore:
    return _knowledge_store
