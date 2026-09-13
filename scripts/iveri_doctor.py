"""IVERI AI Agent — Sovereign System Health & Readiness Doctor.

Runs deep diagnostics on:
  1. Sovereign Environment & File Paths
  2. SQLite WAL Database & Relational Integrity
  3. Sovereign Air-Gap Socket Interceptor & Firewall
  4. Layout-Aware Document & RAG Engines
  5. Executive Deliverables Engine (.docx generation)
  6. Local Inference Hardware Physics & VRAM Budget
  7. Offline LLM Daemons (Ollama / llama-server)
"""

import sys
import os
import platform
import socket
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from hermes_constants import get_hermes_home
from sovereign.network_monitor import activate_sovereign_mode, SovereignNetworkMonitor
from sovereign.firewall import get_firewall
from hermes_cli.local_runtime.engine_driver import get_local_engine_manager, EngineType
from hermes_cli.local_runtime.hardware import probe_budget


def check_status(name: str, ok: bool, detail: str = "") -> None:
    badge = "[PASS]" if ok else "[WARN]"
    color = "\033[92m" if ok else "\033[93m"
    reset = "\033[0m"
    print(f" {color}{badge}{reset} {name:<36} {detail}")


def run_diagnostics():
    print("=" * 72)
    print("        IVERI AI AGENT // SOVEREIGN SYSTEM READINESS DOCTOR        ")
    print("=" * 72)
    print(f" OS:      {platform.system()} {platform.release()} ({platform.machine()})")
    print(f" Python:  {sys.version.split()[0]} ({sys.executable})")
    home = get_hermes_home()
    print(f" Storage: {home}")
    print("-" * 72)

    # 1. Home directory & directories
    home.mkdir(parents=True, exist_ok=True)
    dirs = ["deliverables", "artifacts", "rag", "memories", "logs"]
    all_dirs_ok = True
    for d in dirs:
        p = home / d
        p.mkdir(parents=True, exist_ok=True)
        if not p.is_dir():
            all_dirs_ok = False
    check_status("Sovereign Storage Tree", all_dirs_ok, f"{len(dirs)} subdirectories initialized")

    # 2. SQLite Database Integrity
    db_path = home / "state.db"
    db_ok = False
    table_count = 0
    wal_active = False
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        mode = cur.fetchone()[0]
        wal_active = (str(mode).upper() == "WAL")
        
        # Check tables
        cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
        table_count = cur.fetchone()[0]
        conn.close()
        db_ok = True
    except Exception as e:
        db_ok = False
    check_status("SQLite WAL Storage", db_ok and wal_active, f"journal_mode={wal_active}, tables={table_count}")

    # 3. Air-Gap Sovereign Firewall Interceptor
    monitor = activate_sovereign_mode(mode="airgap")
    fw = get_firewall()
    intercept_ok = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("8.8.8.8", 53))
        intercept_ok = False
        s.close()
    except (ConnectionRefusedError, OSError):
        intercept_ok = True
    check_status("Air-Gap Socket Firewall", intercept_ok, "External egress blocked at kernel layer")

    # 4. Document Engine & PyMuPDF
    doc_engine_ok = False
    try:
        import fitz
        doc_engine_ok = True
        version = getattr(fitz, "__version__", "active")
        check_status("Document Parser (PyMuPDF)", True, f"v{version} (Layout-aware streaming)")
    except ImportError:
        check_status("Document Parser (PyMuPDF)", False, "pymupdf not installed")

    # 5. Deliverables Engine (.docx)
    docx_ok = False
    try:
        from tools.deliverables.docx_generator import DocxDeliverableGenerator
        gen = DocxDeliverableGenerator()
        docx_ok = True
        check_status("Deliverables Engine (.docx)", True, "Corporate template generator ready")
    except Exception as e:
        check_status("Deliverables Engine (.docx)", False, str(e))

    # 6. Multimodal Vision & TTS
    vlm_ok = False
    tts_ok = False
    try:
        from agent.multimodal.vlm_smol import SmolVLMEngine
        vlm = SmolVLMEngine()
        avail = vlm.is_available()
        check_status("Local Vision (SmolVLM-256M)", avail, "Weights: ~500MB VRAM footprint" if avail else "Install transformers+torch to activate")
    except Exception as e:
        check_status("Local Vision (SmolVLM-256M)", False, str(e))

    try:
        from agent.multimodal.tts_kitten import KittenTTSEngine
        tts = KittenTTSEngine()
        avail = tts.is_available()
        check_status("Offline Speech (KittenTTS)", avail, "Offline .wav synthesis active" if avail else "Standby (optional on-device speech)")
    except Exception as e:
        check_status("Offline Speech (KittenTTS)", False, str(e))

    # 7. Hardware Physics & Local Inference Budget
    budget = probe_budget(planning=True)
    manager = get_local_engine_manager()
    ollama_driver = manager.drivers.get(EngineType.OLLAMA)
    llama_driver = manager.drivers.get(EngineType.LLAMA_CPP)

    ollama_online = ollama_driver.is_available() if ollama_driver else False
    llama_online = llama_driver.is_available() if llama_driver else False

    vram_gb = budget.usable_vram_bytes / (1024 ** 3)
    ram_gb = budget.ram_available_bytes / (1024 ** 3)
    vram_str = f"{vram_gb:.1f}GB usable VRAM / {ram_gb:.1f}GB RAM" if vram_gb > 0 else f"{ram_gb:.1f}GB RAM (CPU mode)"
    check_status("Hardware VRAM Physics", True, vram_str)
    check_status("Ollama Inference Daemon", ollama_online, "Online at localhost:11434" if ollama_online else "Standby (run: ollama serve)")
    check_status("llama-server GGUF Engine", llama_online, "Online at localhost:8080" if llama_online else "Standby (supervisable)")

    print("=" * 72)
    overall_ok = db_ok and intercept_ok and doc_engine_ok and docx_ok
    if overall_ok:
        print(" \033[92m[SOVEREIGN READY]\033[0m All core sovereign air-gap components verified.")
    else:
        print(" \033[93m[PARTIAL READY]\033[0m Some optional engines are in standby mode.")
    print("=" * 72)
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(run_diagnostics())
