# IVERI AI Agent — Backend Schema & Storage Specification

**Document Version:** 1.0.0  
**Database Engine:** SQLite 3.45+ (WAL Mode Enabled)  
**File Location:** `$IVERI_HOME/state.db` (Default: `~/.iveri/state.db` on Unix, `%LOCALAPPDATA%/iveri/state.db` on Windows)  
**Encoding:** UTF-8  
**Concurrency Model:** Single Writer / Bounded LIFO Reader Pool  

---

## 1. Storage Topology & Filesystem Layout

All state, persistent memory, indexed knowledge, and execution logs reside deterministically under the `IVERI_HOME` directory:

```
$IVERI_HOME/
├── state.db                     # Core SQLite database (metadata, transcripts, RAG, audit)
├── state.db-wal                 # SQLite Write-Ahead Log
├── state.db-shm                 # SQLite Shared Memory
├── config.yaml                  # Non-secret configuration & user preferences
├── .env                         # Encrypted secrets & optional cloud API keys
├── memories/
│   ├── MEMORY.md                # Agent curated facts, standing rules, cross-session notes
│   ├── USER.md                  # User profile, role, environment, and preferences
│   └── .locks/                  # Cross-process advisory file locks
├── runtimes/                    # Supervised inference binaries
│   └── llamacpp/                # Managed llama-server binaries (CUDA, Vulkan, CPU)
├── models/                      # Local GGUF weights & Hugging Face caches
├── workspaces/                  # NotebookLLM document vaults (raw PDFs, drawings, code)
├── deliverables/                # Synthesized output files (.docx, .xlsx, .pptx)
└── logs/
    ├── agent.log                # INFO+ core application runtime logs
    ├── errors.log               # WARNING+ diagnostic log
    └── network_audit.log        # Cryptographically verifiable socket interceptor logs
```

---

## 2. Entity-Relationship Architecture

```
┌────────────────────────┐       1:N       ┌────────────────────────┐
│        sessions        ├─────────────────┤        messages        │
│ ---------------------- │                 │ ---------------------- │
│ id (PK)                │                 │ id (PK AUTOINCREMENT)  │
│ session_key            │                 │ session_id (FK)        │
│ system_prompt_hash(FK) ├────────┐        │ role, content          │
│ parent_session_id (FK) │        │        │ tool_calls, tool_name  │
└────────────────────────┘        │        │ active, compacted      │
                                  │        └───────────┬────────────┘
                                  │                    │ Virtual FTS Sync
                                  │                    ▼
┌────────────────────────┐        │        ┌────────────────────────┐
│     system_prompts     │        │        │      messages_fts      │
│ ---------------------- │        │        │ ---------------------- │
│ hash (PK)              │◄───────┘        │ content, tool_calls    │
│ prompt (TEXT)          │                 │ (FTS5 Tokenizer)       │
└────────────────────────┘                 └────────────────────────┘

┌────────────────────────┐       1:N       ┌────────────────────────┐
│    rag_collections     ├─────────────────┤     rag_documents      │
│ ---------------------- │                 │ ---------------------- │
│ id (PK)                │                 │ id (PK)                │
│ name (UNIQUE)          │                 │ collection_id (FK)     │
└────────────────────────┘                 │ path, doc_hash, mtime  │
                                           └───────────┬────────────┘
                                                       │ 1:N
                                                       ▼
┌────────────────────────┐       1:N       ┌────────────────────────┐
│     rag_chunks_fts     │◄────────────────┤       rag_chunks       │
│ ---------------------- │   FTS5 Sync     │ ---------------------- │
│ content (FTS5 BM25)    │                 │ id (PK), document_id   │
└────────────────────────┘                 │ chunk_index, content   │
                                           │ embedding (BLOB/Vec)   │
                                           └────────────────────────┘
```

---

## 3. Core Database DDL Specification

### 3.1 Schema Versioning & System Prompts
```sql
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

-- Content-addressed system prompt store (deduplicates large prompt strings)
CREATE TABLE IF NOT EXISTS system_prompts (
    hash TEXT PRIMARY KEY,
    prompt TEXT NOT NULL,
    created_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
);
```

### 3.2 Sessions Table
Tracks conversational sessions, lifecycle status, git contexts, token usage, and billing.
```sql
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,                         -- 'cli', 'desktop', 'web', 'telegram', etc.
    session_key TEXT NOT NULL,                    -- Platform routing tuple
    user_id TEXT,
    chat_id TEXT,
    thread_id TEXT,
    model TEXT NOT NULL,                          -- Model identifier or local quant name
    model_config TEXT,                            -- JSON: temperature, top_p, branch markers
    system_prompt_hash TEXT REFERENCES system_prompts(hash),
    parent_session_id TEXT REFERENCES sessions(id), -- Lineage pointer for forks & compactions
    started_at REAL NOT NULL,
    ended_at REAL,
    end_reason TEXT,                              -- 'compression', 'session_reset', 'agent_close'
    
    -- Token Accounting Metrics
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    estimated_cost_usd REAL DEFAULT 0.0,
    actual_cost_usd REAL DEFAULT 0.0,
    
    -- Git Workspace Telemetry
    cwd TEXT,
    git_branch TEXT,
    git_repo_root TEXT,
    git_metadata_generation INTEGER DEFAULT 0,
    
    -- UI Lifecycle & Status
    archived INTEGER DEFAULT 0,
    pinned INTEGER DEFAULT 0,
    hidden INTEGER DEFAULT 0,
    last_read_at REAL,
    last_activity_ts REAL
);

CREATE INDEX IF NOT EXISTS idx_sessions_key ON sessions(session_key);
CREATE INDEX IF NOT EXISTS idx_sessions_parent ON sessions(parent_session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at DESC);
```

### 3.3 Messages Table
Incremental transcript ledger storing multimodal turns, tool execution requests, and reasoning payloads.
```sql
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('system', 'user', 'assistant', 'tool')),
    content TEXT,                                 -- Raw text or JSON array for multimodal blocks
    tool_call_id TEXT,                           -- Identifier matching assistant tool_calls
    tool_calls TEXT,                             -- JSON array of function call invocations
    tool_name TEXT,                              -- Invoked function name for 'tool' role rows
    timestamp REAL NOT NULL,
    token_count INTEGER DEFAULT 0,
    finish_reason TEXT,                          -- 'stop', 'tool_calls', 'length'
    
    -- Reasoning Engine Fields
    reasoning TEXT,                              -- Internal thinking tokens
    reasoning_content TEXT,
    
    -- Durability & Compaction Flags
    active INTEGER DEFAULT 1,                     -- 1 = Live context; 0 = Rewound / compacted
    compacted INTEGER DEFAULT 0,                  -- 1 = Soft-archived by compaction summary
    api_content TEXT,                             -- Exact serialized string sent to LLM wire
    display_identity TEXT,                       -- SHA-256 generation hash
    display_order INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session_order ON messages(session_id, display_order);
CREATE INDEX IF NOT EXISTS idx_messages_session_active ON messages(session_id, active);
```

### 3.4 Full-Text Search Virtual Tables (FTS5)
Provides sub-millisecond BM25 keyword matching and trigram substring search for code and CJK scripts.
```sql
-- External-content FTS5 table indexing message turns
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    tool_name,
    tool_calls,
    content='messages',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);

-- Triggers maintaining messages_fts sync on write/update/delete
CREATE TRIGGER IF NOT EXISTS trg_messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content, tool_name, tool_calls)
    VALUES (new.id, new.content, new.tool_name, new.tool_calls);
END;

CREATE TRIGGER IF NOT EXISTS trg_messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content, tool_name, tool_calls)
    VALUES ('delete', old.id, old.content, old.tool_name, old.tool_calls);
END;

CREATE TRIGGER IF NOT EXISTS trg_messages_au AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content, tool_name, tool_calls)
    VALUES ('delete', old.id, old.content, old.tool_name, old.tool_calls);
    INSERT INTO messages_fts(rowid, content, tool_name, tool_calls)
    VALUES (new.id, new.content, new.tool_name, new.tool_calls);
END;
```

---

## 4. IVERI Sovereign & Knowledge Fabric Extensions

### 4.1 Knowledge Fabric: Document & Vector Tables
```sql
CREATE TABLE IF NOT EXISTS rag_collections (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS rag_documents (
    id TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL REFERENCES rag_collections(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    doc_hash TEXT NOT NULL,                       -- SHA-256 of file content to detect drift
    mtime REAL NOT NULL,                          -- Last modified timestamp
    chunk_count INTEGER DEFAULT 0,
    created_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS rag_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding BLOB,                              -- Float32 array serialized as binary BLOB
    metadata_json TEXT,                          -- Section headers, page numbers, AST scope
    created_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_doc ON rag_chunks(document_id);

-- FTS5 Search for Hybrid RAG BM25 Retrieval
CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts USING fts5(
    content,
    content='rag_chunks',
    content_rowid='rowid',
    tokenize='unicode61'
);
```

### 4.2 Sovereign Network Audit Log Table
Stores persistent, tamper-evident verification records of all network events observed by `SovereignNetworkMonitor`.
```sql
CREATE TABLE IF NOT EXISTS network_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    mode TEXT NOT NULL,                           -- 'air_gapped', 'lan_only', 'selective', 'online'
    destination_ip TEXT NOT NULL,
    destination_port INTEGER NOT NULL,
    hostname TEXT,
    is_local INTEGER NOT NULL CHECK(is_local IN (0, 1)),
    allowed INTEGER NOT NULL CHECK(allowed IN (0, 1)),
    blocked_reason TEXT,
    process_pid INTEGER NOT NULL,
    sha256_attestation TEXT                       -- HMAC-SHA256 signature validating entry integrity
);

CREATE INDEX IF NOT EXISTS idx_network_audit_ts ON network_audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_network_audit_allowed ON network_audit_log(allowed);
```

### 4.3 Deliverables & Generated Artifacts Table
Maintains metadata and audit trails for all formal corporate artifacts produced by the agent.
```sql
CREATE TABLE IF NOT EXISTS deliverables_artifacts (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    title TEXT NOT NULL,
    format TEXT NOT NULL CHECK(format IN ('docx', 'xlsx', 'pptx', 'pdf', 'binary')),
    file_path TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    sha256_checksum TEXT NOT NULL,
    template_name TEXT,
    created_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_deliverables_session ON deliverables_artifacts(session_id);
```

---

## 5. Concurrency Control & Database Maintenance

### 5.1 PRAGMA Optimization Directives
Upon opening every database connection in `hermes_state_dbfile.py`, the following runtime pragma configurations are enforced:
```sql
PRAGMA journal_mode = WAL;          -- Concurrent readers with single non-blocking writer
PRAGMA synchronous = NORMAL;        -- Safe on modern filesystems with 3x write throughput
PRAGMA foreign_keys = ON;           -- Enforce relational referential integrity
PRAGMA busy_timeout = 30000;        -- 30-second lock retry before throwing database busy error
PRAGMA cache_size = -64000;         -- Allocate 64MB memory page cache per connection
PRAGMA temp_store = MEMORY;         -- Virtual temp tables held resident in RAM
PRAGMA mmap_size = 268435456;       -- 256MB memory-mapped I/O for lightning FTS scans
```

### 5.2 Compaction & Context Pruning Rules
1. **Tool Result Pruning**: When a conversation transcript nears token window exhaustion ($>85\%$), the agent invokes `prune_tool_results()` marking old intermediary tool results (`active = 0`), which shrinks token volume without calling an LLM.
2. **Summary Compaction**: Older message turns are synthesized into structured checkpoints. Predecessor rows are marked `compacted = 1` and hidden from model prompt construction, while remaining fully visible in user-facing UI history.
3. **Vacuum & WAL Checkpointing**: `PRAGMA wal_checkpoint(TRUNCATE);` is automatically executed during graceful application shutdown, keeping `state.db` compact and single-file portable.
