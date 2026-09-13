"""IVERI AI Agent — Local Inference Engine Driver.

Unified abstraction for managing local inference backends:
- LlamaCppDriver: Supervised native llama-server binaries (CUDA, Metal, Vulkan, CPU)
- OllamaDriver: Local Ollama daemon management (REST API / tags / pull / serve)
- Hardware-fit estimation & auto-quantization selection
"""

import abc
import json
import logging
import os
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class EngineType(Enum):
    """Supported local engine backends."""
    LLAMA_CPP = "llama_cpp"
    OLLAMA = "ollama"
    VLLM = "vllm"


@dataclass
class LocalModelInfo:
    """Metadata describing an installed or downloaded local model."""
    name: str
    engine: EngineType
    size_bytes: int = 0
    quantization: str = "Unknown"
    parameter_count: str = "Unknown"
    context_length: int = 32768
    path_or_tag: str = ""
    is_running: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


class ILocalEngineDriver(abc.ABC):
    """Abstract interface for local inference engines."""

    @abc.abstractmethod
    def engine_type(self) -> EngineType:
        """Return the engine identifier."""
        pass

    @abc.abstractmethod
    def is_available(self) -> bool:
        """True if the engine binary or daemon is installed and reachable."""
        pass

    @abc.abstractmethod
    def list_installed_models(self) -> List[LocalModelInfo]:
        """List all models currently downloaded/registered in this engine."""
        pass

    @abc.abstractmethod
    def get_base_url(self) -> str:
        """Return the OpenAI-compatible HTTP base URL for inference."""
        pass


class OllamaDriver(ILocalEngineDriver):
    """Driver for managing Ollama local daemon."""

    def __init__(self, host: Optional[str] = None):
        self.host = host or os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")

    def engine_type(self) -> EngineType:
        return EngineType.OLLAMA

    def get_base_url(self) -> str:
        return f"{self.host}/v1"

    def is_available(self) -> bool:
        """Check if Ollama service is listening."""
        try:
            req = urllib.request.Request(f"{self.host}/api/version", method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def list_installed_models(self) -> List[LocalModelInfo]:
        """Query native GET /api/tags from Ollama."""
        models: List[LocalModelInfo] = []
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for m in data.get("models", []):
                    details = m.get("details", {})
                    models.append(
                        LocalModelInfo(
                            name=m.get("name", ""),
                            engine=EngineType.OLLAMA,
                            size_bytes=m.get("size", 0),
                            quantization=details.get("quantization_level", "Unknown"),
                            parameter_count=details.get("parameter_size", "Unknown"),
                            path_or_tag=m.get("name", ""),
                            details=details,
                        )
                    )
        except Exception as e:
            logger.debug("Failed to query Ollama models: %s", e)
        return models


class LlamaCppDriver(ILocalEngineDriver):
    """Driver for managing supervised llama.cpp / llama-server."""

    def __init__(self, port: int = 8080):
        self.port = port
        self.base_url = f"http://127.0.0.1:{self.port}/v1"

    def engine_type(self) -> EngineType:
        return EngineType.LLAMA_CPP

    def get_base_url(self) -> str:
        return self.base_url

    def is_available(self) -> bool:
        """Check if llama.cpp binaries exist or server is active."""
        # Check active server probe
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}/health", method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass

        # Check binary availability
        try:
            from hermes_cli.local_runtime.binaries import installed_tags
            return len(installed_tags()) > 0
        except Exception:
            return False

    def list_installed_models(self) -> List[LocalModelInfo]:
        """Scan catalog and local GGUF cache."""
        from hermes_constants import get_hermes_home
        models_dir = get_hermes_home() / "models"
        models: List[LocalModelInfo] = []
        if not models_dir.exists():
            return models

        for root, _, files in os.walk(models_dir):
            for file in files:
                if file.endswith(".gguf"):
                    full_path = os.path.join(root, file)
                    try:
                        size = os.path.getsize(full_path)
                    except OSError:
                        size = 0
                    models.append(
                        LocalModelInfo(
                            name=file.replace(".gguf", ""),
                            engine=EngineType.LLAMA_CPP,
                            size_bytes=size,
                            path_or_tag=full_path,
                        )
                    )
        return models


class LocalEngineManager:
    """Unified coordinator across local inference runtimes."""

    def __init__(self):
        self.drivers: Dict[EngineType, ILocalEngineDriver] = {
            EngineType.OLLAMA: OllamaDriver(),
            EngineType.LLAMA_CPP: LlamaCppDriver(),
        }

    def get_active_driver(self) -> Optional[ILocalEngineDriver]:
        """Return the first available local engine driver."""
        for driver in self.drivers.values():
            if driver.is_available():
                return driver
        return None

    def list_all_local_models(self) -> List[LocalModelInfo]:
        """Aggregate all installed models across all local backends."""
        all_models: List[LocalModelInfo] = []
        for driver in self.drivers.values():
            all_models.extend(driver.list_installed_models())
        return all_models

    def assess_hardware_fit(self, model_name: str, quant: str = "Q4_K_M", est_gb: float = 5.8) -> Dict[str, Any]:
        """Assess whether a model will fit in resident VRAM using hardware budget probe."""
        from hermes_cli.local_runtime.hardware import probe_budget

        budget = probe_budget(planning=True)
        usable_vram_gb = budget.usable_vram_bytes / (1024 ** 3)
        total_ram_gb = budget.ram_available_bytes / (1024 ** 3)
        needed_gb = est_gb

        fits_on_gpu = usable_vram_gb >= needed_gb
        fits_on_ram = (total_ram_gb * 0.75) >= needed_gb

        return {
            "model": model_name,
            "quant": quant,
            "needed_gb": round(needed_gb, 2),
            "available_vram_gb": round(usable_vram_gb, 2),
            "available_ram_gb": round(total_ram_gb, 2),
            "is_uma": budget.uma,
            "fits_100_percent_gpu": fits_on_gpu,
            "spills_to_ram": not fits_on_gpu and fits_on_ram,
            "unsupported": not fits_on_gpu and not fits_on_ram,
            "status_label": (
                "[GREEN] GPU Accelerated (Fastest)" if fits_on_gpu
                else "[AMBER] Spills to System RAM (Moderate)" if fits_on_ram
                else "[RED] Insufficient Memory"
            ),
        }



# Singleton manager
_manager = LocalEngineManager()


def get_local_engine_manager() -> LocalEngineManager:
    return _manager
