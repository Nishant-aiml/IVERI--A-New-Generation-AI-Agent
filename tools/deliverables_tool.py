"""IVERI AI Agent — Deliverables Tool.

Enables the agent to autonomously generate professional statutory approval notes,
memos, and inspection reports as native .docx files and register them as versioned Artifacts.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from tools.registry import registry
from tools.deliverables.docx_generator import get_docx_generator
from agent.artifacts import Artifact, get_artifact_manager

logger = logging.getLogger(__name__)

GENERATE_DOCUMENT_SCHEMA: Dict[str, Any] = {
    "name": "generate_document",
    "description": "Generate a formal corporate deliverable (.docx) such as a statutory approval note, inspection report, or technical memo with structured tables and signatures.",
    "parameters": {
        "type": "object",
        "properties": {
            "format": {
                "type": "string",
                "enum": ["docx"],
                "description": "Output document format (currently supports 'docx')",
            },
            "title": {
                "type": "string",
                "description": "Formal title of the document or approval note",
            },
            "department": {
                "type": "string",
                "description": "Department or organization issuing the document (e.g. 'Inspection & Maintenance Dept, MRPL')",
            },
            "subject": {
                "type": "string",
                "description": "Brief subject statement describing the approval sought or finding",
            },
            "background": {
                "type": "string",
                "description": "Background narrative and operational context",
            },
            "findings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of key technical findings or inspection observations",
            },
            "recommendations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of proposed actions or approvals requested",
            },
            "table_data": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "description": "2D array representing tabular parameters, limits, and readings (row 0 is header)",
            },
            "financial_implications": {
                "type": "string",
                "description": "Optional financial estimates, cost of replacement, or budgetary impact",
            },
            "signatories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of official review roles or approving authorities",
            },
            "classification": {
                "type": "string",
                "description": "Security classification banner (default: 'CONFIDENTIAL // INTERNAL ONLY')",
            },
        },
        "required": ["format", "title", "department", "subject", "background", "findings", "recommendations"],
    },
}


def _handle_generate_document(args: Dict[str, Any], **kwargs) -> str:
    """Handler for generate_document tool call."""
    title = args.get("title", "Approval Note")
    department = args.get("department", "Engineering Dept")
    subject = args.get("subject", "Statutory Review")
    background = args.get("background", "")
    findings = args.get("findings", [])
    recommendations = args.get("recommendations", [])
    table_data = args.get("table_data")
    financial = args.get("financial_implications")
    signatories = args.get("signatories")
    classification = args.get("classification", "CONFIDENTIAL // INTERNAL ONLY")

    gen = get_docx_generator()
    file_path = gen.generate_approval_note(
        title=title,
        department=department,
        subject=subject,
        background=background,
        findings=findings,
        recommendations=recommendations,
        table_data=table_data,
        financial_implications=financial,
        signatories=signatories,
        classification=classification,
    )

    # Register as an Artifact
    artifact_mgr = get_artifact_manager()
    artifact = Artifact(
        identifier=title.lower().replace(" ", "_"),
        type="application/docx",
        title=title,
        content=f"Statutory Document: {title}\nPath: {file_path}",
        file_path=file_path,
    )
    artifact_mgr.save_artifact(artifact)

    return json.dumps({
        "status": "success",
        "message": f"Document successfully generated and registered as Artifact: {title}",
        "file_path": file_path,
        "artifact_identifier": artifact.identifier,
        "version": artifact.version,
    })


# Register tool
registry.register(
    name="generate_document",
    toolset="deliverables",
    schema=GENERATE_DOCUMENT_SCHEMA,
    handler=_handle_generate_document,
    emoji="📄",
)
