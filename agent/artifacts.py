"""IVERI AI Agent — Claude & Grok Style Artifacts Subsystem.

Manages dedicated artifacts (code files, markdown memos, HTML widgets, SVG graphics,
Word/Excel/PPT deliverables) rendered in a dedicated side-panel rather than cluttering
the conversational chat stream.

Supports:
- Structured XML tag extraction:
    <iveri_artifact identifier="my_doc" type="application/vnd.ant.markdown" title="My Document">
    ...content...
    </iveri_artifact>
  (Also backward-compatible with <antArtifact> tags).
- Version tracking (v1, v2, etc. upon in-place edits).
- Local filesystem persistence under `$IVERI_HOME/artifacts/<session_id>/`.
- JSON-RPC event broadcast for desktop/web side drawers.
"""

import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Pattern matching both <iveri_artifact> and legacy <antArtifact> tags
ARTIFACT_REGEX = re.compile(
    r"<(?:iveri_artifact|antArtifact)\s+([^>]+)>(.*?)</(?:iveri_artifact|antArtifact)>",
    re.DOTALL | re.IGNORECASE,
)

# Attribute extraction inside tag header
ATTR_REGEX = re.compile(r'([a-zA-Z0-9_\-]+)\s*=\s*["\']([^"\']+)["\']')


@dataclass
class Artifact:
    """A self-contained substantial deliverable or code file."""
    identifier: str
    type: str                          # 'application/vnd.ant.code', 'application/vnd.ant.markdown', 'text/html', 'application/docx'
    title: str
    content: str
    version: int = 1
    session_id: str = "default"
    language: Optional[str] = None
    file_path: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ArtifactManager:
    """Manages creation, parsing, versioning, and storage of artifacts."""

    def __init__(self, storage_root: Optional[Path] = None):
        from hermes_constants import get_hermes_home
        self.storage_root = storage_root or (get_hermes_home() / "artifacts")
        self.storage_root.mkdir(parents=True, exist_ok=True)
        # In-memory index: session_id -> identifier -> Artifact
        self._registry: Dict[str, Dict[str, Artifact]] = {}
        self._listeners: List[Callable[[Artifact, str], None]] = []

    def add_listener(self, listener: Callable[[Artifact, str], None]) -> None:
        """Register a callback for artifact lifecycle events (event: 'created' or 'updated')."""
        self._listeners.append(listener)

    def _notify(self, artifact: Artifact, event: str) -> None:
        for listener in self._listeners:
            try:
                listener(artifact, event)
            except Exception as e:
                logger.error("Error in artifact listener: %s", e)

    def _scan_session_disk(self, session_id: str) -> None:
        """Scan disk for persisted artifacts in session directory."""
        session_dir = self.storage_root / session_id
        if not session_dir.exists():
            return
        if session_id not in self._registry:
            self._registry[session_id] = {}

        for meta_file in session_dir.glob("*.meta.json"):
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
                art = Artifact(**data)
                self._registry[session_id][art.identifier] = art
            except Exception as e:
                logger.debug("Failed to read artifact meta %s: %s", meta_file, e)

    def get_artifact(self, session_id: str, identifier: str) -> Optional[Artifact]:
        """Retrieve an artifact by session ID and identifier."""
        if session_id not in self._registry or identifier not in self._registry[session_id]:
            self._scan_session_disk(session_id)
        return self._registry.get(session_id, {}).get(identifier)

    def list_artifacts(self, session_id: str) -> List[Artifact]:
        """List all artifacts generated within a session."""
        self._scan_session_disk(session_id)
        return list(self._registry.get(session_id, {}).values())

    def save_artifact(self, artifact: Artifact) -> Artifact:
        """Persist artifact to disk and update registry."""
        session_dir = self.storage_root / artifact.session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        if artifact.session_id not in self._registry:
            self._registry[artifact.session_id] = {}
            self._scan_session_disk(artifact.session_id)

        existing = self._registry[artifact.session_id].get(artifact.identifier)
        event = "created"
        if existing:
            artifact.version = existing.version + 1
            event = "updated"

        ext = self._guess_extension(artifact.type, artifact.language)
        filename = f"{artifact.identifier}_v{artifact.version}.{ext}"
        target_path = session_dir / filename

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(artifact.content)

        artifact.file_path = str(target_path)
        artifact.updated_at = time.time()

        # Save metadata sidecar for cross-process recovery
        meta_path = session_dir / f"{filename}.meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(artifact.to_dict()))

        self._registry[artifact.session_id][artifact.identifier] = artifact
        self._notify(artifact, event)
        logger.info(
            "ARTIFACT %s: '%s' (v%d) -> %s",
            event.upper(), artifact.title, artifact.version, target_path
        )
        return artifact

    def extract_artifacts_from_text(self, text: str, session_id: str = "default") -> List[Artifact]:

        """Parse all <iveri_artifact> tags from text, save them, and return list."""
        artifacts: List[Artifact] = []

        for match in ARTIFACT_REGEX.finditer(text):
            attr_str = match.group(1)
            content = match.group(2).strip()

            attrs = dict(ATTR_REGEX.findall(attr_str))
            identifier = attrs.get("identifier") or attrs.get("id") or f"artifact_{int(time.time())}"
            artifact_type = attrs.get("type", "text/plain")
            title = attrs.get("title", identifier.replace("_", " ").title())
            language = attrs.get("language")

            artifact = Artifact(
                identifier=identifier,
                type=artifact_type,
                title=title,
                content=content,
                session_id=session_id,
                language=language,
            )
            saved = self.save_artifact(artifact)
            artifacts.append(saved)

        return artifacts

    def strip_artifacts_from_text(self, text: str, replacement_template: str = "[Artifact: {title}]") -> str:
        """Replace verbose artifact blocks with clean inline summary references."""
        def _repl(match):
            attrs = dict(ATTR_REGEX.findall(match.group(1)))
            title = attrs.get("title") or attrs.get("identifier") or "Deliverable"
            return replacement_template.format(title=title)

        return ARTIFACT_REGEX.sub(_repl, text)

    def _guess_extension(self, artifact_type: str, language: Optional[str] = None) -> str:
        """Derive standard file extension from MIME type or language."""
        if language:
            lang_map = {
                "python": "py", "javascript": "js", "typescript": "ts", "html": "html",
                "css": "css", "c++": "cpp", "c": "c", "rust": "rs", "go": "go",
                "markdown": "md", "json": "json", "yaml": "yaml", "sql": "sql",
            }
            if language.lower() in lang_map:
                return lang_map[language.lower()]

        type_map = {
            "application/vnd.ant.code": "txt",
            "application/vnd.ant.markdown": "md",
            "text/markdown": "md",
            "text/html": "html",
            "image/svg+xml": "svg",
            "application/json": "json",
            "application/docx": "docx",
            "application/xlsx": "xlsx",
            "application/pptx": "pptx",
        }
        return type_map.get(artifact_type, "txt")


# Module-level singleton
_manager = ArtifactManager()


def get_artifact_manager() -> ArtifactManager:
    return _manager
