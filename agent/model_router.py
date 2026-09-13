"""IVERI AI Agent — Task-Aware Model Router.

Automatically classifies user requests and routes tasks to the best available
open-weight or cloud model based on task requirements:
- Coding requests -> Coding-specialized models (e.g. Qwen2.5-Coder, DeepSeek-Coder)
- Document OCR / Diagram / P&ID -> Multimodal Vision models (e.g. Qwen2.5-VL, SmolVLM)
- Mathematical / Multi-step Reasoning -> Deep reasoning models (e.g. DeepSeek-R1, Llama-3.3-70B)
- General conversation / Simple edits -> Fast lightweight models (e.g. Qwen-7B, Llama-8B)
"""

import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TaskCategory(Enum):
    """Categorized task profiles requiring different model specialties."""
    CODING = "coding"
    MULTIMODAL_VISION = "multimodal_vision"
    REASONING_SYNTHESIS = "reasoning_synthesis"
    GENERAL = "general"


@dataclass
class ModelProfile:
    """Specification of an available model's strengths and requirements."""
    model_id: str
    display_name: str
    provider: str                      # 'custom', 'ollama', 'anthropic', 'openai-codex', etc.
    primary_category: TaskCategory
    context_window: int = 32768
    supports_tools: bool = True
    supports_vision: bool = False
    is_local: bool = True
    min_vram_gb: float = 6.0
    aliases: List[str] = field(default_factory=list)


# Standard task profiles and candidate model preferences
DEFAULT_TASK_PREFERENCES: Dict[TaskCategory, List[str]] = {
    TaskCategory.CODING: [
        "qwen2.5-coder-32b",
        "qwen2.5-coder-7b",
        "deepseek-coder-v2",
        "claude-3-7-sonnet",
        "gpt-4o",
    ],
    TaskCategory.MULTIMODAL_VISION: [
        "qwen2.5-vl-72b",
        "qwen2.5-vl-7b",
        "smolvlm-256m",
        "internvl2-26b",
        "claude-3-7-sonnet",
        "gpt-4o",
    ],
    TaskCategory.REASONING_SYNTHESIS: [
        "deepseek-r1",
        "llama-3.3-70b-instruct",
        "qwen2.5-72b-instruct",
        "claude-3-7-sonnet",
    ],
    TaskCategory.GENERAL: [
        "qwen2.5-7b-instruct",
        "llama-3.1-8b-instruct",
        "mistral-nemo-12b",
    ],
}


class TaskClassifier:
    """Zero-shot rule & heuristic classifier for user turns."""

    # Keywords indicating code generation, refactoring, or tool testing
    CODE_PATTERNS = [
        r"\b(def|class|function|async|await|return|import|export|const|let|var)\b",
        r"\b(python|javascript|typescript|c\+\+|rust|golang|sql|html|css|bash|powershell)\b",
        r"\b(bug|fix|error|traceback|exception|compile|syntax|refactor|test|unit\s*test|pytest)\b",
        r"\b(docker|dockerfile|git|github|ci\/cd|pipeline|regex|script)\b",
        r"```[a-zA-Z0-9_\-+]*\n",  # Code fence in input
    ]

    # Keywords indicating scanned document extraction, images, or drawings
    VISION_PATTERNS = [
        r"\b(image|picture|photo|screenshot|diagram|drawing|p&id|piping|blueprint)\b",
        r"\b(scanned|ocr|handwriting|handwritten|inspect|chart|graph|schematic)\b",
        r"\.(png|jpg|jpeg|webp|gif|bmp|tiff|pdf|dwg|dxf)\b",
    ]

    # Keywords indicating complex document synthesis, approvals, or calculations
    REASONING_PATTERNS = [
        r"\b(approval\s*note|executive\s*summary|statutory|board\s*note|memorandum|tender)\b",
        r"\b(calculate|calculation|heat\s*balance|mass\s*balance|audit|compliance|sop)\b",
        r"\b(synthesize|comprehensive\s*report|root\s*cause|investigation|findings)\b",
    ]

    def __init__(self):
        self._compiled_code = [re.compile(p, re.IGNORECASE) for p in self.CODE_PATTERNS]
        self._compiled_vision = [re.compile(p, re.IGNORECASE) for p in self.VISION_PATTERNS]
        self._compiled_reasoning = [re.compile(p, re.IGNORECASE) for p in self.REASONING_PATTERNS]

    def classify(self, user_prompt: str, attachments: Optional[List[str]] = None) -> Tuple[TaskCategory, str]:
        """Classify user intent into a TaskCategory and return the rationale."""
        # 1. Attachments take immediate priority
        if attachments:
            for att in attachments:
                lower = att.lower()
                if any(lower.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".pdf", ".dwg"]):
                    return TaskCategory.MULTIMODAL_VISION, f"Visual/document attachment detected ({os.path.basename(att)})"

        # 2. Check for explicit vision/image requests
        vision_matches = sum(1 for cp in self._compiled_vision if cp.search(user_prompt))
        if vision_matches >= 2 or re.search(r"\b(p&id|engineering drawing|scanned)\b", user_prompt, re.IGNORECASE):
            return TaskCategory.MULTIMODAL_VISION, f"Document/image inspection requested ({vision_matches} matching signals)"

        # 3. Check for code syntax & developer keywords
        code_matches = sum(1 for cp in self._compiled_code if cp.search(user_prompt))
        if code_matches >= 2:
            return TaskCategory.CODING, f"Software engineering task detected ({code_matches} code signals)"

        # 4. Check for deep industrial reasoning / note generation
        reasoning_matches = sum(1 for cp in self._compiled_reasoning if cp.search(user_prompt))
        if reasoning_matches >= 1:
            return TaskCategory.REASONING_SYNTHESIS, f"Industrial reasoning/approval task detected ({reasoning_matches} signals)"

        # 5. Fallback: single code signal or default general conversation
        if code_matches >= 1:
            return TaskCategory.CODING, "Single software engineering keyword detected"

        return TaskCategory.GENERAL, "Standard query or general conversational task"


class TaskAwareModelRouter:
    """Routes requests to the optimal local or cloud model."""

    def __init__(self):
        self.classifier = TaskClassifier()
        self.registered_models: Dict[str, ModelProfile] = {}
        self.routing_history: List[Dict[str, Any]] = []

    def register_model(self, profile: ModelProfile) -> None:
        """Register an active or local model profile."""
        self.registered_models[profile.model_id.lower()] = profile
        for alias in profile.aliases:
            self.registered_models[alias.lower()] = profile

    def select_model(
        self,
        user_prompt: str,
        attachments: Optional[List[str]] = None,
        available_models: Optional[List[str]] = None,
        manual_override: Optional[str] = None,
    ) -> Tuple[str, TaskCategory, str]:
        """Select the best model for the current task.
        
        Returns:
            Tuple of (selected_model_id, detected_category, rationale)
        """
        # Manual override takes precedence
        if manual_override and manual_override.strip():
            cat, _ = self.classifier.classify(user_prompt, attachments)
            return manual_override.strip(), cat, "User explicit manual override"

        category, rationale = self.classifier.classify(user_prompt, attachments)
        preferred_candidates = DEFAULT_TASK_PREFERENCES.get(category, [])

        available_lower = [m.lower() for m in (available_models or [])]

        # Match preference list against currently available models
        if available_lower:
            for candidate in preferred_candidates:
                for avail in available_lower:
                    if candidate in avail or avail in candidate:
                        self._log_decision(category, avail, rationale)
                        return avail, category, f"Auto-selected for {category.value}: matched candidate '{avail}' ({rationale})"

            # If no candidate matched, pick the first available
            fallback = available_models[0]
            self._log_decision(category, fallback, rationale)
            return fallback, category, f"Fallback to first available model '{fallback}' ({rationale})"

        # If no available models list supplied, return the top preference for this category
        selected = preferred_candidates[0] if preferred_candidates else "qwen2.5-coder-7b"
        self._log_decision(category, selected, rationale)
        return selected, category, f"Auto-selected top profile '{selected}' ({rationale})"

    def _log_decision(self, category: TaskCategory, model: str, reason: str) -> None:
        """Log routing decisions for sovereign telemetry and demo auditing."""
        record = {
            "category": category.value,
            "selected_model": model,
            "reason": reason,
        }
        self.routing_history.append(record)
        logger.info("MODEL ROUTER: %s -> %s [Reason: %s]", category.value.upper(), model, reason)

    def get_latest_routing_decision(self) -> Optional[Dict[str, Any]]:
        """Return the most recent routing audit entry."""
        return self.routing_history[-1] if self.routing_history else None


# Module-level singleton
_router = TaskAwareModelRouter()


def get_router() -> TaskAwareModelRouter:
    """Return the global model router instance."""
    return _router


def route_task(prompt: str, attachments: Optional[List[str]] = None, available_models: Optional[List[str]] = None) -> Tuple[str, str, str]:
    """Convenience helper returning (model_id, category_name, rationale)."""
    model_id, category, rationale = _router.select_model(prompt, attachments, available_models)
    return model_id, category.value, rationale
