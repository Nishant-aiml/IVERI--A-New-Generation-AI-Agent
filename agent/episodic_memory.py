"""IVERI AI Agent — Episodic Memory Engine.

Enables the agent to learn from its own past mistakes across sessions:
- Captures tool execution failures, traceback errors, and runtime corrections.
- Indexes episodic experiences: (Task Context, Failed Attempt, Root Cause, Verified Fix).
- Retrieves relevant past episodes before executing tools to prevent repeating errors.
- Operates 100% offline, persisting episodes to `$IVERI_HOME/memories/EPISODES.md`
  and SQLite `state.db`.
"""

import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Episode:
    """A record of a mistake, tool failure, or user correction with its verified resolution."""
    task_context: str
    failed_action: str
    error_message: str
    resolution: str
    tool_name: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    occurrence_count: int = 1

    def to_markdown(self) -> str:
        """Format as a readable markdown block for prompt context."""
        return (
            f"### Incident: {self.task_context[:80]}\n"
            f"- **Tool / Action:** `{self.tool_name or 'general'}`\n"
            f"- **Error Encountered:** {self.error_message[:200]}\n"
            f"- **Learned Fix:** {self.resolution}\n"
        )


class EpisodicMemoryStore:
    """Stores and retrieves past operational episodes to avoid repeating errors."""

    def __init__(self, storage_dir: Optional[Path] = None):
        from hermes_constants import get_hermes_home
        self.storage_dir = storage_dir or (get_hermes_home() / "memories")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.episodes_file = self.storage_dir / "EPISODES.md"
        self._episodes: List[Episode] = []
        self._load_episodes()

    def _load_episodes(self) -> None:
        """Load episodes from disk if present."""
        if not self.episodes_file.exists():
            return
        try:
            content = self.episodes_file.read_text(encoding="utf-8")
            # Parse markdown sections
            raw_blocks = content.split("\n§\n")
            for block in raw_blocks:
                lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
                if len(lines) >= 3:
                    # Extract fields via simple parsing
                    ctx = lines[0].replace("### Incident:", "").strip()
                    tool = "general"
                    err = ""
                    fix = ""
                    for line in lines[1:]:
                        if line.startswith("- **Tool / Action:**"):
                            tool = line.split("`")[1] if "`" in line else "general"
                        elif line.startswith("- **Error Encountered:**"):
                            err = line.replace("- **Error Encountered:**", "").strip()
                        elif line.startswith("- **Learned Fix:**"):
                            fix = line.replace("- **Learned Fix:**", "").strip()

                    if fix:
                        self._episodes.append(
                            Episode(task_context=ctx, failed_action="", error_message=err, resolution=fix, tool_name=tool)
                        )
        except Exception as e:
            logger.warning("Failed to load episodic memories: %s", e)

    def record_mistake(
        self,
        task_context: str,
        failed_action: str,
        error_message: str,
        resolution: str,
        tool_name: Optional[str] = None,
    ) -> Episode:
        """Record a learned lesson from a failed attempt and verified fix."""
        # Deduplicate if identical error already known
        clean_err = error_message[:150].strip()
        for ep in self._episodes:
            if clean_err and clean_err in ep.error_message:
                ep.occurrence_count += 1
                ep.resolution = resolution  # update with latest verified fix
                self._save_to_disk()
                return ep

        episode = Episode(
            task_context=task_context.strip(),
            failed_action=failed_action.strip(),
            error_message=clean_err,
            resolution=resolution.strip(),
            tool_name=tool_name,
        )
        self._episodes.append(episode)
        self._save_to_disk()
        logger.info("EPISODIC MEMORY: Recorded new lesson for tool '%s'", tool_name or 'general')
        return episode

    def retrieve_relevant_lessons(self, query: str, tool_name: Optional[str] = None, limit: int = 3) -> List[Episode]:
        """Find past mistakes relevant to the current task or tool."""
        matches: List[Episode] = []
        query_words = set(re.findall(r"\w+", query.lower()))

        for ep in self._episodes:
            score = 0
            if tool_name and ep.tool_name and tool_name.lower() == ep.tool_name.lower():
                score += 3
            ep_words = set(re.findall(r"\w+", (ep.task_context + " " + ep.error_message).lower()))
            common = query_words.intersection(ep_words)
            score += len(common)

            if score > 0:
                matches.append((score, ep))

        matches.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matches[:limit]]

    def _save_to_disk(self) -> None:
        """Persist all episodes to EPISODES.md with section delimiters."""
        try:
            blocks = [ep.to_markdown() for ep in self._episodes]
            full_content = "\n§\n\n".join(blocks)
            self.episodes_file.write_text(full_content, encoding="utf-8")
        except Exception as e:
            logger.error("Failed to persist episodic memory: %s", e)


# Module-level singleton
_episodic_store = EpisodicMemoryStore()


def get_episodic_store() -> EpisodicMemoryStore:
    return _episodic_store
