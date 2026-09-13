"""IVERI AI Agent — Word Document Generator.

Generates professional, standardized corporate deliverables (.docx):
- Statutory approval notes
- Inspection reports & audit findings
- Executive memos with tables, headers, and signature blocks
Outputs files directly into `$IVERI_HOME/deliverables/` and registers them as Artifacts.
"""

import logging
import os
import re
import time
from pathlib import Path

from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DocxDeliverableGenerator:
    """Generates structured DOCX documents."""

    def __init__(self, output_dir: Optional[Path] = None):
        from hermes_constants import get_hermes_home
        self.output_dir = output_dir or (get_hermes_home() / "deliverables")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_approval_note(
        self,
        title: str,
        department: str,
        subject: str,
        background: str,
        findings: List[str],
        recommendations: List[str],
        financial_implications: Optional[str] = None,
        table_data: Optional[List[List[str]]] = None,
        signatories: Optional[List[str]] = None,
        classification: str = "CONFIDENTIAL // INTERNAL ONLY",
    ) -> str:
        """Generate a formal statutory approval note in DOCX format."""
        import docx
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT

        doc = docx.Document()

        # Set standard margins
        for section in doc.sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)

        # 1. Header / Classification Watermark
        p_class = doc.add_paragraph()
        p_class.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_class = p_class.add_run(f"[{classification}]")
        r_class.font.size = Pt(8.5)
        r_class.font.bold = True
        r_class.font.color.rgb = RGBColor(180, 0, 0)

        # 2. Document Title
        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_title = p_title.add_run(title.upper())
        r_title.font.size = Pt(16)
        r_title.font.bold = True

        p_dept = doc.add_paragraph()
        p_dept.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_dept = p_dept.add_run(f"Department: {department} | Date: {time.strftime('%d-%b-%Y')}")
        r_dept.font.size = Pt(10)
        r_dept.font.italic = True

        doc.add_paragraph().paragraph_format.space_after = Pt(10)

        # 3. Subject Line
        p_subj = doc.add_paragraph()
        r_subj_tag = p_subj.add_run("SUBJECT: ")
        r_subj_tag.bold = True
        p_subj.add_run(subject)
        p_subj.paragraph_format.space_after = Pt(14)

        # 4. Background Section
        h_bg = doc.add_heading("1. Background & Context", level=1)
        h_bg.paragraph_format.space_before = Pt(12)
        doc.add_paragraph(background)

        # 5. Key Findings Section
        h_find = doc.add_heading("2. Key Inspection Findings / Analysis", level=1)
        h_find.paragraph_format.space_before = Pt(12)
        for idx, finding in enumerate(findings, 1):
            doc.add_paragraph(f"{idx}. {finding}")

        # 6. Structured Data Table (if provided)
        if table_data and len(table_data) > 0:
            doc.add_heading("Summary of Data & Parameters", level=2)
            table = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.style = "Light Shading Accent 1" if "Light Shading Accent 1" in [s.name for s in doc.styles] else "Table Grid"

            for r_idx, row in enumerate(table_data):
                for c_idx, cell in enumerate(row):
                    cell_obj = table.cell(r_idx, c_idx)
                    cell_obj.text = str(cell)
                    if r_idx == 0:
                        for p in cell_obj.paragraphs:
                            for r in p.runs:
                                r.bold = True

        # 7. Financial Implications (if applicable)
        if financial_implications:
            h_fin = doc.add_heading("3. Financial & Operational Implications", level=1)
            h_fin.paragraph_format.space_before = Pt(12)
            doc.add_paragraph(financial_implications)

        # 8. Recommendations / Approval Sought
        h_rec = doc.add_heading("4. Proposal & Approvals Sought", level=1)
        h_rec.paragraph_format.space_before = Pt(12)
        for idx, rec in enumerate(recommendations, 1):
            doc.add_paragraph(f"{idx}. {rec}")

        # 9. Signatures Block
        doc.add_paragraph().paragraph_format.space_after = Pt(20)
        h_sig = doc.add_heading("5. Reviewers & Approving Authorities", level=1)
        sig_list = signatories or ["Inspecting Engineer", "Head of Maintenance", "General Manager (Operations)"]
        
        sig_table = doc.add_table(rows=2, cols=len(sig_list))
        sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for idx, name in enumerate(sig_list):
            cell_top = sig_table.cell(0, idx)
            cell_top.text = "\n\n________________________\n"
            cell_bot = sig_table.cell(1, idx)
            cell_bot.text = f"{name}\nSignature & Date"

        # Save to deliverables directory
        filename = f"{re.sub(r'[^a-zA-Z0-9_-]', '_', title)}_{int(time.time())}.docx"
        target_path = self.output_dir / filename
        doc.save(str(target_path))
        logger.info("DOCX DELIVERABLE GENERATED: %s", target_path)
        return str(target_path)


_docx_generator = DocxDeliverableGenerator()


def get_docx_generator() -> DocxDeliverableGenerator:
    return _docx_generator
