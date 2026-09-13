# IVERI AI Agent — Product Requirements Document (PRD)

**Document Version:** 1.0.0  
**Status:** Approved / Baseline  
**Product Classification:** Sovereign On-Premise Autonomous AI Workbench & Developer Engine  
**Author / Engineering Lead:** AI Systems Engineering Team  
**Confidentiality:** Public Product Specification  

---

## 1. Executive Summary & Universal Mission

### 1.1 Product Vision
**IVERI AI Agent** is the world's first unified, sovereign, air-gapped AI agent workbench built for **every single human being on planet Earth**—from students and independent developers to researchers, creators, global enterprises, and sovereign defense refineries. 

IVERI combines:
- The autonomous software engineering capabilities of **Claude Code and Devin** (filesystem navigation, terminal execution, AST parsing, and autonomous self-healing).
- The document analysis and synthesis of **NotebookLLM** (layout-aware streaming of 500+ page technical manuals and books with table preservation via OpenDataLoader).
- The interactive visual side-drawer of **Claude and Grok Artifacts** (code execution, SVG diagrams, and executive deliverables).
- The uncompromising zero-leakage security posture of defense systems (inspired by SecureForgeAI and MRPL Problem Statement 26117).

**Sole Owners & Authors**: Ishwari Bhoyar (`ishwaribhoyar2@gmail.com`) & Nishant Bhoyar (`dattanishant2@gmail.com`).

### 1.2 The Problem
1. **AI Centralization & Privacy Stripping**: Mainstream AI platforms require sending sensitive thoughts, research, source code, and confidential documents to centralized cloud servers with invasive telemetry and data mining.
2. **Subscription Paywalls & Fragility**: Essential intelligence is gated behind recurring monthly subscription fees ($20–$500/month). When the internet disconnects or APIs throttle, productivity halts.
3. **Fragmentation of Specialized Tools**: Users must juggle separate apps for coding (Cursor), document reading (NotebookLLM), terminal automation, and speech.
4. **Strict Industrial & Defense Air-Gaps**: Refineries, hospitals, defense labs, and law firms are legally barred from using cloud models due to zero-trust compliance requirements.

### 1.3 The Solution
IVERI AI Agent provides a single, 100% sovereign workbench that:
- Runs **100% offline** on consumer laptops or enterprise GPU servers with zero external network connectivity.
- Is **free forever for everyone** running on local hardware at ₹0 cost.
- Automatically selects the optimal local open-weight model based on task classification (Qwen-Coder for code, SmolVLM for vision, DeepSeek-R1 for reasoning).
- Produces **hard deliverables** (native `.docx` approval notes, `.xlsx` calculations, compilable code, `.wav` speech) with interactive Artifacts.
- Enforces a kernel socket interceptor that physically guarantees zero data exfiltration.

---

## 2. Target Audience & Universal User Personas

IVERI is architected for every user tier across the globe:

| Persona | Domain | Primary Challenge | IVERI Sovereign Solution |
| :--- | :--- | :--- | :--- |
| **Aarav K. (Student / Researcher)** | Academic Lab / University | Needs to cross-examine 1,000+ page textbooks (e.g. Russell & Norvig) without paying SaaS subscriptions. | Uses IVERI locally on laptop; ingests 500+ page PDFs with table preservation; gets instant grounded answers with citations for ₹0. |
| **Ananya T. (Solo Developer / Creator)** | Open-Source Software | Wants Devin-class autonomous coding and Claude-style Artifacts without $500/month SaaS lock-in. | Runs IVERI CLI / Desktop REPL. IVERI writes multi-file features, runs tests, fixes compiler bugs, and renders live code previews. |
| **Chief Inspector Rajesh** | Petrochemical Refinery / Energy | Must review 80-page scanned vendor inspection PDFs and P&ID diagrams daily; cannot use cloud AI due to secrecy. | Uses IVERI Sovereign Workbench. Local VLM extracts diagrams, compares with indexed SOPs, generates compliant `.docx` approval note in 90 seconds. |
| **Vikram S.** | Defense & Embedded Systems | Writing telemetry code for air-gapped embedded systems with zero internet access allowed. | Runs IVERI natively against local GGUF models. IVERI patches code and verifies tests with zero outbound packets guaranteed. |

---

## 3. Product Pillars & Competitive Differentiation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            IVERI AI AGENT CORE                              │
├──────────────────────┬──────────────────────┬───────────────────────────────┤
│ 1. SOVEREIGN ENGINE  │ 2. AGENTIC WORKBENCH │ 3. DELIVERABLES SYNTHESIZER   │
│ • Air-gapped proof   │ • 40+ native tools   │ • Native .docx / .xlsx / .pptx│
│ • Socket interceptor │ • Subagent delegation│ • Formatted engineering notes │
│ • Zero telemetry     │ • Interactive REPL   │ • Verified compilable code    │
├──────────────────────┼──────────────────────┼───────────────────────────────┤
│ 4. MULTI-MODEL ROUTE │ 5. KNOWLEDGE FABRIC  │ 6. SECUREFORGE CYBERPUNK UX   │
│ • Auto-task detection│ • Hybrid RAG (Dense) │ • Real-time telemetry dashboard│
│ • llama.cpp + Ollama │ • BM25 FTS5 + Trigram│ • Module status monitors      │
│ • 39 cloud providers │ • Local OCR / VLM    │ • One-click air-gap switcher  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Competitive Matrix

| Capability | Claude Code | Cursor | NotebookLLM | AnythingLLM | IVERI AI Agent |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Air-Gapped / 100% Offline** | ❌ No | ❌ No | ❌ No | ⚠️ Partial | ✅ **Native Zero-Net** |
| **Autonomous Multi-File Coding** | ✅ Yes | ⚠️ Semi | ❌ No | ❌ No | ✅ **Full Engine** |
| **Browser & Terminal Execution** | ⚠️ Term only | ❌ No | ❌ No | ❌ No | ✅ **7 Backends + CDP** |
| **Scanned OCR / P&ID Vision** | ❌ No | ❌ No | ⚠️ Text PDF | ❌ No | ✅ **Local VLM + OCR** |
| **Deliverable Gen (.docx/.xlsx)**| ❌ No | ❌ No | ❌ Audio/text | ❌ No | ✅ **Direct Generation**|
| **Multi-Model Auto-Routing** | ❌ Anthropic | ❌ Cloud | ❌ Gemini | ❌ Manual | ✅ **Automated Task Hub**|
| **Hardware Fit Estimation** | ❌ No | ❌ No | ❌ No | ❌ No | ✅ **Physics-Based VRAM**|
| **Exfiltration Audit Proof** | ❌ No | ❌ No | ❌ No | ❌ No | ✅ **Socket Interceptor**|

---

## 4. Functional Specifications

### 4.1 Feature Set A: Sovereign & Air-Gapped Operation
- **FS-A1: Application-Level Network Sandbox**: Enforces strict socket-level filtering (`sovereign/network_monitor.py`). In `air_gapped` mode, non-loopback connections throw instant `ConnectionRefusedError`.
- **FS-A2: Exfiltration Proof Telemetry**: Real-time counter of total packets, internal IPC calls, and external attempts blocked. Exportable cryptographic audit certificate (`audit_report.json` with SHA-256 integrity stamp).
- **FS-A3: Mode Switcher**: Runtime toggle between `AIR_GAPPED`, `LAN_ONLY`, `SELECTIVE` (whitelisted IP/domain for enterprise model servers), and `ONLINE`.

### 4.2 Feature Set B: Task-Aware Model Orchestration
- **FS-B1: Zero-Config Task Classifier**: Inspects user intent, input modalities, and attachment types before turn execution.
- **FS-B2: Specialized Routing Matrix**:
  - *Code Generation / Debugging*: Routed to `qwen2.5-coder-32b`, `deepseek-coder-v2`, or local 7B quantization.
  - *Document OCR / Diagram Inspection*: Routed to `qwen2.5-vl`, `internvl2`, or on-device OCR pipeline.
  - *Complex Reasoning / Note Synthesis*: Routed to `deepseek-r1` or `llama-3.3-70b-instruct`.
- **FS-B3: Local Model Marketplace ("Cookbook++")**: Catalog of verified GGUF quants with automatic VRAM physics estimation (`hardware.py` & `estimator.py`) ensuring zero out-of-memory crashes.

### 4.3 Feature Set C: NotebookLLM-Class Knowledge Fabric
- **FS-C1: Document Workspace**: Drag-and-drop vault for manuals, SOPs, tenders, and internal code repositories.
- **FS-C2: Dual-Stage Hybrid Search**: Combines semantic embeddings (via fastembed / nomic-embed) with SQLite FTS5 BM25 keyword and trigram matching using Reciprocal Rank Fusion (RRF).
- **FS-C3: Multi-Document Synthesis**: Cross-document thematic analysis, timeline extraction, and contradiction detection across multiple source documents.

### 4.4 Feature Set D: Deliverables Engine
- **FS-D1: Word Document Synthesis (`.docx`)**: Automated generation of statutory approval notes, executive briefings, and audit memos based on pre-loaded institutional templates.
- **FS-D2: Spreadsheet Synthesis (`.xlsx`)**: Step-by-step engineering calculations with embedded formulas, cost comparisons, and automated chart generation.
- **FS-D3: Presentation Decks (`.pptx`)**: Formatted multi-slide decks with key takeaways, visual placeholders, and technical architecture blocks.
- **FS-D4: Production Code Binaries**: Compiles, runs tests in Docker/sandbox backends, and outputs cryptographically signed binaries.

### 4.5 Feature Set E: SecureForge Cyberpunk Interface & Developer REPL
- **FS-E1: Unified Desktop Experience**: Modern Electron / Native desktop workspace with high-contrast telemetry meters (FPS, VRAM, Token/sec, Memory Ring status).
- **FS-E2: Resilient REPL (CLI)**: Interactive prompt_toolkit REPL supporting slash commands (`/model`, `/sovereign`, `/audit`, `/workspace`, `/deliverable`).
- **FS-E3: Messaging Adapters**: Headless gateway connecting to Telegram, Discord, Slack, WhatsApp, and Webhooks for non-air-gapped remote operations.

---

## 5. Non-Functional Requirements (NFR)

### 5.1 Performance & Latency
- **Time to First Token (TTFT)**: <= 1.2 s for 8B local models on NVIDIA RTX 3060 / Apple M2 (16GB).
- **Inference Throughput**: Minimum 35 tokens/sec for coding models on mid-tier hardware.
- **FTS Search Latency**: <= 45 ms over a corpus of 100,000 document chunks and message records.
- **UI Responsiveness**: 60 FPS continuous rendering for telemetry gauges and terminal stream buffers.

### 5.2 Security & Compliance
- **Zero Remote Telemetry**: No tracking, phone-home pings, or analytics beacons.
- **Data-at-Rest Security**: AES-256 encrypted SQLite storage for session state and document embeddings.
- **Process Isolation**: Terminal commands run in unprivileged subshells or isolated Docker environments (`tools/environments/docker.py`).
- **Prompt Injection Defense**: Multi-tier sanitization of external documents before injection into the prompt context window.

### 5.3 Reliability & Durability
- **Process Crash Recovery**: SQLite WAL-mode state engine guarantees that if a process is killed mid-turn, the transcript, tool call state, and incomplete artifacts are fully recoverable upon restart.
- **Prompt Cache Stability**: Strict byte-stability of the system prompt ensures maximum upstream KV-cache utilization, reducing compute overhead by up to 80%.

---

## 6. Packaging, Monetization & Go-To-Market

### 6.1 Distribution Formats
1. **Desktop Native**: Windows `.exe` / macOS `.dmg` / Linux `.AppImage`.
2. **Enterprise Docker**: `docker compose up -d` single-command air-gapped cluster including Chroma/SQLite-vec, SearXNG, and llama-server.
3. **Developer CLI**: Self-contained pip binary (`iveri`) installable into clean Python virtual environments.

### 6.2 Low-Risk / High-Reward Tiering

```
┌───────────────────────────┬───────────────────────────┬───────────────────────────┐
│        COMMUNITY          │      PRO WORKBENCH        │   ENTERPRISE SOVEREIGN    │
│       ₹0 / FOREVER        │        ₹799 / mo          │     ₹10L - ₹50L / yr      │
├───────────────────────────┼───────────────────────────┼───────────────────────────┤
│ • Full local LLM runtime  │ • Community features +    │ • Full on-prem installation│
│ • 40+ built-in core tools │ • Managed Cloud AI Proxy  │ • Unlimited seat licenses │
│ • Local RAG & FTS5 search │   (Claude, GPT, Gemini)   │ • Air-gapped audit bundle │
│ • Air-gapped sovereign net│ • Live Web Search RAG     │ • Custom P&ID VLM tuning  │
│ • Document Gen (.docx)    │ • Multi-device cloud sync │ • Direct engineering SLA  │
│ • CLI & Desktop interfaces│ • Priority model registry │ • Custom SOP ingestion pipeline│
└───────────────────────────┴───────────────────────────┴───────────────────────────┘
```

---

## 7. Release Milestones

- **Milestone 1 (Week 1–2)**: *Sovereign Core & Rebranding* — Complete codebase refactor from Hermes to IVERI, integration of socket network monitor, validation of offline CLI.
- **Milestone 2 (Week 3–4)**: *Model Router & Deliverables Engine* — Task classifier, python-docx/pptx/xlsx generators, MRPL inspection report demonstration.
- **Milestone 3 (Week 5–8)**: *Knowledge Fabric & Desktop GUI* — Local vector RAG integration, Electron SecureForge cyberpunk UI, live telemetry dashboard.
- **Milestone 4 (Week 9–12)**: *Enterprise Hardening* — Docker air-gap package, single-click Windows `.exe` installer, multi-user role management.
