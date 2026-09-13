# IVERI AI Agent — Technical Requirements Document (TRD)

**Document Version:** 1.0.0  
**Target Environment:** Local Workstations (Windows 10/11 x64, macOS Apple Silicon, Linux x86_64) & Air-Gapped GPU Clusters  
**Author / System Architect:** Principal AI System Architect  
**Architecture Base:** Hermes Kernel Fork (MIT) + IVERI Sovereign Extensions  

---

## 1. System Architecture Overview

IVERI AI Agent operates on an **in-process kernel / out-of-process worker** model. The agent core is deterministic, state-persisted, and modularized into decoupled mixins and sibling modules.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             PRESENTATION TIER                               │
│  Electron (Desktop GUI) │ prompt_toolkit (CLI REPL) │ FastAPI Gateway (Web) │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ JSON-RPC 2.0 / WebSocket / IPC
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          IVERI AGENT CONTROL PLANE                          │
│  AIAgent (14 Mixins) │ Task Router │ Model Dispatcher │ Sovereign Guard     │
└──────┬───────────────────────┬───────────────────────────────┬──────────────┘
       │                       │                               │
       ▼                       ▼                               ▼
┌──────────────┐     ┌──────────────────┐            ┌────────────────────────┐
│ TOOL RUNTIME │     │ LOCAL RAG & FTS5 │            │ LOCAL INFERENCE ENGINE │
│ • 40+ Core   │     │ • SQLite FTS5    │            │ • llama-server (GGUF)  │
│ • Sandboxes  │     │ • sqlite-vec     │            │ • Ollama / vLLM Driver │
│ • Doc Synth  │     │ • FastEmbed      │            │ • Hardware Estimator   │
│ • Playwright │     │ • Document Parser│            │ • Speculative Decoder  │
└──────┬───────┘     └─────────┬────────┘            └───────────┬────────────┘
       │                       │                                 │
       ▼                       ▼                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PERSISTENCE & SECURITY RING                         │
│   state.db (SQLite WAL) │ Socket Filter (NetworkMonitor) │ AES-256 Vault    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Specifications

### 2.1 AIAgent Core Loop (`run_agent.py` & `agent/turn_*.py`)
- **Loop Pattern**: Iterative turn execution loop bounded by dynamic `IterationBudget` and hard iteration limits (`max_iterations = 30`).
- **Durability Invariant**: Every assistant tool call is committed to SQLite `state.db` **prior** to invoking tool handlers. If the process is halted or power fails during a tool execution, session resume reconstructs the active turn without regenerating calls.
- **Turn Phases**:
  1. `turn_facade_lease`: Durable cross-process session turn acquisition.
  2. `turn_context`: Byte-stable system prompt generation, user message assembly, and `<memory-context>` fence injection.
  3. `turn_api_retry_loop`: Multi-attempt LLM invocation with exponential backoff on 429/503 errors and credential fallback.
  4. `turn_tool_round`: Parallel non-destructive tool dispatch (`execute_tool_calls_concurrent`) and sequential destructive write execution.
  5. `turn_finalizer`: Token accounting, billing metrics, and dispatching non-blocking background memory reviews.

### 2.2 Sovereign Network Isolation (`sovereign/network_monitor.py`)
- **Hook Technique**: Intercepts `socket.socket.connect` and `socket.socket.connect_ex` at runtime in the Python interpreter.
- **Enforcement Rules**:
  ```python
  def _should_block(self, event: NetworkEvent) -> bool:
      if self.mode == NetworkMode.ONLINE:
          return False
      if event.is_local: # 127.0.0.1, ::1, RFC1918 Private LAN
          return False
      if self.mode == NetworkMode.AIR_GAPPED:
          return True  # Immediate ConnectionRefusedError
      if self.mode == NetworkMode.LAN_ONLY:
          return not event.is_private_ip
      if self.mode == NetworkMode.SELECTIVE:
          return event.destination_ip not in self.whitelist
      return False
  ```
- **Audit Verification**: SHA-256 attested audit record storing timestamp, PID, destination tuple `(ip, port)`, and enforcement disposition.

### 2.3 Task-Aware Model Router (`agent/model_router.py`)
- **Heuristic Classifier**: Zero-shot input analyzer extracting:
  - AST code intent keywords (`def `, `class `, `import `, `git `, syntax snippets) -> `CODING`.
  - Binary and visual attachments (`.pdf`, `.png`, `.jpg`, `.dwg`, `.dxf`) -> `MULTIMODAL_OCR`.
  - Document synthesis queries (`approval note`, `board memo`, `SOP`, `summarize`) -> `REASONING_SYNTHESIS`.
- **Model Dynamic Allocation**:
  - Dynamically switches backend client endpoint `base_url` and model slug per turn without invalidating session context.
  - Transparently manages Ollama `keep_alive` or llama.cpp process spawning to free GPU VRAM when switching between 32B coding models and 70B reasoning models.

### 2.4 Deliverables Generation Engine (`tools/deliverables/`)
- **DOCX Engine (`docx_generator.py`)**:
  - Uses `python-docx` to construct strictly formatted corporate documents.
  - Supports dynamic table generation, header/footer branding, classification watermarks ("CONFIDENTIAL // INTERNAL ONLY"), and standardized approval signature blocks.
- **XLSX Engine (`xlsx_generator.py`)**:
  - Uses `openpyxl` to produce computational workbooks.
  - Automatically injects Excel formulas (`SUM`, `VLOOKUP`, `AVERAGE`, `IRR`) rather than hardcoded calculated values, allowing live recalculation by human auditors.
- **PPTX Engine (`pptx_generator.py`)**:
  - Uses `python-pptx` with predefined master slide layouts for executive briefings, technical designs, and root cause analyses.

### 2.5 Hybrid Knowledge Fabric & Vector RAG (`agent/rag/`)
- **Vector Storage**: `sqlite-vec` extension loaded directly into `state.db` or embedded LanceDB instance. Zero separate vector server processes needed.
- **Local Embedding Provider**: `fastembed` running ONNX-optimized `nomic-embed-text-v1.5` (512 dimensions, quantized, 8x faster than PyTorch CPU).
- **Hybrid Retrieval Algorithm (Reciprocal Rank Fusion)**:
  $$\text{RRF\_Score}(d) = \sum_{m \in \{\text{Dense}, \text{BM25}\}} \frac{1}{60 + \text{Rank}_m(d)}$$
- **Chunking Pipeline**:
  - Text & Markdown: Recursive character chunking (1000 chars, 200 overlap) with header preservation.
  - Python / C++ / Rust: AST-aware chunking using Tree-Sitter grammar boundaries to ensure functions are never severed across chunks.

---

## 3. Communication Protocols & Interfaces

### 3.1 TUI & Desktop JSON-RPC 2.0 API (`tui_gateway/server.py`)
The desktop client interacts with the agent kernel over standard WebSocket (`/api/ws`) or stdio using JSON-RPC 2.0:

```json
// Client Request: Prompt Submit
{
  "jsonrpc": "2.0",
  "id": "req-101",
  "method": "prompt.submit",
  "params": {
    "session_id": "sess_01J7XZ...",
    "prompt": "Analyze inspection_report.pdf and generate approval_note.docx",
    "attachments": [{"path": "/data/inspection_report.pdf", "type": "application/pdf"}],
    "model_override": null,
    "mode": "air_gapped"
  }
}

// Server Event: Streaming Output Delta
{
  "jsonrpc": "2.0",
  "method": "message.delta",
  "params": {
    "session_id": "sess_01J7XZ...",
    "role": "assistant",
    "delta": "Initiating on-device OCR scan of 8-page document..."
  }
}

// Server Event: Tool Execution Notification
{
  "jsonrpc": "2.0",
  "method": "tool.start",
  "params": {
    "session_id": "sess_01J7XZ...",
    "tool_name": "generate_document",
    "args": {"format": "docx", "template": "refinery_approval"}
  }
}
```

### 3.2 Security Dashboard Telemetry API (`/api/sovereign/telemetry`)
Emits 1 Hz structured JSON payloads reporting:
```json
{
  "network_mode": "air_gapped",
  "is_sovereign": true,
  "external_calls_attempted": 0,
  "external_calls_blocked": 0,
  "internal_ipc_count": 1420,
  "hardware": {
    "gpu_name": "NVIDIA RTX 4090",
    "vram_allocated_mb": 14250,
    "vram_total_mb": 24576,
    "gpu_utilization_pct": 84,
    "temperature_c": 62
  },
  "inference": {
    "active_model": "qwen2.5-coder-32b-instruct-q4_k_m.gguf",
    "tokens_per_second": 48.2,
    "context_tokens_used": 14320,
    "context_tokens_max": 32768
  }
}
```

---

## 4. Hardware Optimization & Local Inference Specs

### 4.1 Quantization & VRAM Footprint Targets

| Model Target | Architecture | Quantization | Context Window | Min VRAM Required | Optimal Hardware |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Qwen 2.5 Coder 7B** | Dense | Q4_K_M | 32k | 5.8 GB | RTX 3060 (12GB) / M1 (16GB) |
| **Qwen 2.5 Coder 32B** | Dense | Q4_K_M | 32k | 20.2 GB | RTX 3090 / 4090 (24GB) |
| **DeepSeek Coder V2 Lite** | MoE (16B total, 2.4B active) | Q4_K_M | 64k | 10.4 GB | RTX 4070 (12GB) / M2 (16GB) |
| **Qwen 2.5 VL 7B (Vision)** | Multimodal | Q4_K_M | 16k | 7.2 GB | RTX 3060 (12GB) |
| **Llama 3.3 70B** | Dense | Q4_K_M | 32k | 42.0 GB | 2x RTX 3090 / Mac Studio M2 Max (64GB) |

### 4.2 KV Cache Management
- **Paged Attention & KV Quantization**: `llama-server` configured with `--cache-type-k q8_0 --cache-type-v q4_0` reducing KV-cache memory pressure by 40% with zero observable degradation in code synthesis quality.
- **Dynamic Context Growth (`hermes_cli/local_runtime/growth.py`)**: Context window initializes at 8,192 tokens and dynamically resizes as multi-turn conversations extend, avoiding upfront allocation of unneeded VRAM.

---

## 5. Build, Test, and CI/CD Pipeline

### 5.1 Native Packaging Target
- **Windows**: PyInstaller 6.x packaging Python 3.12 64-bit runtime with bundled `tree-sitter`, `sqlite3` (with loadable extension support), and `llama.cpp` AVX2/CUDA binaries into `IVERI_AI_Agent.exe`.
- **Packaging Manifest**: Cryptographic SHA-256 signing of all released binaries.

### 5.2 Test Harness (`scripts/run_tests.sh`)
- **Isolation Sandbox**: Every test run creates an ephemeral `$TMP/iveri_home` redirecting `IVERI_HOME`, `HERMES_HOME`, and `HOME`.
- **Network Invariant Test**: Dedicated test suite asserting that running a full 5-turn coding conversation in sovereign mode produces exactly zero socket connection events outside loopback.
