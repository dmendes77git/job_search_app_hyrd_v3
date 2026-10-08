"""
Company Intelligence Dossier Document Exporter.
Generates executive-grade Microsoft Word (.docx) and Adobe PDF (.pdf) documents
from structured company intelligence dossiers produced by CompanyIntelligenceAgent.

Outputs in-memory BytesIO streams for direct Streamlit download buttons without
writing temporary files to disk.
"""

from __future__ import annotations

import io
import re
from typing import Dict, Any, List
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from fpdf import FPDF


def sanitize_text_for_pdf(text: str) -> str:
    """Sanitize unicode characters to ensure standard Helvetica/Latin-1 PDF font compatibility."""
    if not text:
        return ""
    
    replacements = {
        "—": "-",
        "–": "-",
        "…": "...",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "•": "*",
        "✓": "[X]",
        "✔": "[X]",
        "⚡": "[*]",
        "🎯": "[*]",
        "💼": "[*]",
        "🏢": "[*]",
        "🛡️": "[*]",
        "✨": "[*]",
        "🚀": "[*]",
        "⚙️": "[*]",
        "👥": "[*]",
        "💡": "[*]",
        "📈": "[*]",
        "🏛️": "[*]",
        "🛠️": "[*]",
        "🧭": "[*]",
        "🌍": "[*]",
        "💬": "[*]",
        "⚠️": "[!]",
        "✅": "[OK]",
        "❌": "[X]",
        "→": "->",
        "←": "<-",
        "€": "EUR ",
        "£": "GBP ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Encode to Latin-1 with replace fallback for any unsupported unicode symbols
    return text.encode("latin-1", "replace").decode("latin-1")


def _set_cell_background(cell, fill_hex: str = "F8FAFC") -> None:
    """Helper to apply background color shading to a docx table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex.upper())
    tc_pr.append(shd)


def _set_cell_margins(cell, top: int = 100, bottom: int = 100, left: int = 150, right: int = 150) -> None:
    """Helper to apply internal cell margins (padding) in dxa (1/20 pt)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = OxmlElement("w:tcMar")
    for margin_name, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = OxmlElement(f"w:{margin_name}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tc_mar.append(node)
    tc_pr.append(tc_mar)


def _add_formatted_runs_docx(paragraph, text: str, font_size: float = 10.0, default_color: RGBColor = RGBColor(51, 65, 85)) -> None:
    """Parse basic markdown bold markers (**text**) into styled python-docx runs."""
    parts = re.split(r"(\*\*.*?\*\*)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
            run.font.size = Pt(font_size)
            run.font.color.rgb = RGBColor(15, 23, 42)
        else:
            run = paragraph.add_run(part)
            run.font.size = Pt(font_size)
            run.font.color.rgb = default_color


class DossierPDF(FPDF):
    """Executive PDF renderer for Company Intelligence Dossier."""

    def __init__(self, company_name: str = "Target Company"):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.company_name = sanitize_text_for_pdf(company_name)
        self.set_auto_page_break(auto=True, margin=16)
        self.set_margins(left=18, top=16, right=18)

    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(100, 116, 139)  # #64748b
            self.cell(0, 5, f"COMPANY INTELLIGENCE DOSSIER  |  {self.company_name.upper()}", align="L")
            self.set_draw_color(226, 232, 240)
            self.set_line_width(0.2)
            self.line(18, 22, 192, 22)
            self.ln(7)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)  # #94a3b8
        self.cell(0, 5, f"Hyrd Multi-Agent Career Platform - Confidential Dossier  |  Page {self.page_no()}", align="C")

    def draw_section_heading(self, title: str):
        """Render standard numbered section heading with navy accent and subtle baseline."""
        self.ln(4)
        self.set_font("Helvetica", "B", 11.5)
        self.set_text_color(30, 58, 138)  # Deep Navy #1e3a8a
        self.cell(0, 6, sanitize_text_for_pdf(title.upper()), new_x="LMARGIN", new_y="NEXT")

        # Divider line
        y = self.get_y()
        self.set_draw_color(203, 213, 225)  # Light slate #cbd5e1
        self.set_line_width(0.3)
        self.line(18, y, 192, y)
        self.ln(3)

    def draw_key_metric_row(self, label1: str, val1: str, label2: str, val2: str):
        """Render a clean 2-column key/value metric row with border."""
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 116, 139)  # Slate #64748b
        col_w = 87

        # Labels
        self.cell(col_w, 4.5, sanitize_text_for_pdf(label1.upper()), new_x="RIGHT", new_y="TOP")
        self.cell(col_w, 4.5, sanitize_text_for_pdf(label2.upper()), new_x="LMARGIN", new_y="NEXT")

        # Values
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(15, 23, 42)  # #0f172a
        self.cell(col_w, 5.5, sanitize_text_for_pdf(val1), new_x="RIGHT", new_y="TOP")
        self.cell(col_w, 5.5, sanitize_text_for_pdf(val2), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def draw_bullet(self, text: str, prefix: str = "-"):
        """Render a clean bullet item."""
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(51, 65, 85)
        indent = 4
        curr_x = self.get_x()
        self.set_x(curr_x + indent)
        self.cell(4, 4.5, prefix, new_x="RIGHT", new_y="TOP")
        clean_text = sanitize_text_for_pdf(text)
        self.multi_cell(0, 4.5, clean_text)
        self.ln(1)


def build_dossier_docx(dossier_data: dict) -> io.BytesIO:
    """
    Generates an executive-grade Word (.docx) document from structured company dossier data.
    
    Includes:
    - Executive title banner & corporate identity header
    - Formatted executive summary callout block
    - Business model, funding rounds & valuation metrics table
    - Technology stack & architecture breakdown grid
    - Engineering culture, leadership team & sentiment analysis
    - Strategic interview talking points & questions to ask
    
    Returns an in-memory BytesIO stream ready for direct Streamlit download.
    """
    doc = Document()

    # Configure page geometry (Standard 0.75-inch margins)
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Base styling
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(10)
    normal_style.font.color.rgb = RGBColor(51, 65, 85)

    data = dossier_data or {}
    company_name = data.get("company_name") or "Target Employer"
    stage_info = data.get("stage_and_funding") or {}
    tech_info = data.get("tech_stack") or {}
    culture_info = data.get("engineering_culture") or {}
    leaders = data.get("leadership_team") or []
    momentum = data.get("recent_momentum") or []
    questions = data.get("strategic_interview_questions") or []
    sentiment = data.get("culture_and_sentiment") or {}
    ats_system = data.get("ats_system") or "Ashby / Greenhouse"
    summary_text = data.get("summary") or f"{company_name} corporate profile and strategic intelligence briefing."

    # 1. Title & Header
    p_header = doc.add_paragraph()
    p_header.paragraph_format.space_before = Pt(0)
    p_header.paragraph_format.space_after = Pt(2)
    run_h = p_header.add_run(f"COMPANY INTELLIGENCE DOSSIER")
    run_h.bold = True
    run_h.font.size = Pt(18)
    run_h.font.color.rgb = RGBColor(30, 58, 138)  # Deep Navy

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(8)
    run_sub = p_sub.add_run(f"Employer: {company_name}  |  Stage: {stage_info.get('stage', 'Growth Stage')}  |  ATS: {ats_system}")
    run_sub.font.size = Pt(10.5)
    run_sub.font.color.rgb = RGBColor(100, 116, 139)

    # 2. Executive Summary Callout Box
    table_sum = doc.add_table(rows=1, cols=1)
    table_sum.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell_sum = table_sum.cell(0, 0)
    cell_sum.width = Inches(7.0)
    _set_cell_background(cell_sum, "F1F5F9")  # Soft Slate
    _set_cell_margins(cell_sum, top=140, bottom=140, left=180, right=180)

    p_box = cell_sum.paragraphs[0]
    p_box.paragraph_format.space_before = Pt(2)
    p_box.paragraph_format.space_after = Pt(2)
    p_box.paragraph_format.line_spacing = 1.2
    run_box_label = p_box.add_run("EXECUTIVE SUMMARY:\n")
    run_box_label.bold = True
    run_box_label.font.size = Pt(9.5)
    run_box_label.font.color.rgb = RGBColor(30, 58, 138)
    _add_formatted_runs_docx(p_box, summary_text, font_size=10.0, default_color=RGBColor(30, 41, 59))

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # 3. Section 1: Business Model & Funding Table
    p_s1 = doc.add_paragraph()
    p_s1.paragraph_format.space_before = Pt(12)
    p_s1.paragraph_format.space_after = Pt(4)
    run_s1 = p_s1.add_run("1. BUSINESS MODEL & FINANCIAL OVERVIEW")
    run_s1.bold = True
    run_s1.font.size = Pt(12)
    run_s1.font.color.rgb = RGBColor(30, 58, 138)

    table_fin = doc.add_table(rows=4, cols=2)
    table_fin.alignment = WD_TABLE_ALIGNMENT.CENTER
    fin_data = [
        ("Funding Stage", stage_info.get("stage", "Private / Growth")),
        ("Estimated Valuation / Market Cap", stage_info.get("valuation", "N/A")),
        ("Total Capital Raised", stage_info.get("total_raised", "N/A")),
        ("Headcount & Scale", stage_info.get("headcount", "50 - 500+ employees")),
    ]
    for row_idx, (label, val) in enumerate(fin_data):
        c0 = table_fin.cell(row_idx, 0)
        c1 = table_fin.cell(row_idx, 1)
        c0.width = Inches(3.0)
        c1.width = Inches(4.0)
        _set_cell_background(c0, "F8FAFC" if row_idx % 2 == 0 else "FFFFFF")
        _set_cell_background(c1, "F8FAFC" if row_idx % 2 == 0 else "FFFFFF")
        _set_cell_margins(c0, top=80, bottom=80, left=120, right=120)
        _set_cell_margins(c1, top=80, bottom=80, left=120, right=120)

        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_before = Pt(2)
        p0.paragraph_format.space_after = Pt(2)
        r0 = p0.add_run(label)
        r0.bold = True
        r0.font.size = Pt(9.5)
        r0.font.color.rgb = RGBColor(71, 85, 105)

        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_before = Pt(2)
        p1.paragraph_format.space_after = Pt(2)
        r1 = p1.add_run(str(val))
        r1.font.size = Pt(9.5)
        r1.font.color.rgb = RGBColor(15, 23, 42)

    # Notable Investors
    investors = stage_info.get("notable_investors") or []
    if investors:
        p_inv = doc.add_paragraph()
        p_inv.paragraph_format.space_before = Pt(6)
        p_inv.paragraph_format.space_after = Pt(2)
        r_inv_lbl = p_inv.add_run("Notable Investors: ")
        r_inv_lbl.bold = True
        r_inv_lbl.font.size = Pt(9.5)
        r_inv_lbl.font.color.rgb = RGBColor(30, 58, 138)
        r_inv_val = p_inv.add_run(", ".join(investors))
        r_inv_val.font.size = Pt(9.5)

    # 4. Section 2: Technology Stack & Engineering Architecture
    p_s2 = doc.add_paragraph()
    p_s2.paragraph_format.space_before = Pt(12)
    p_s2.paragraph_format.space_after = Pt(4)
    run_s2 = p_s2.add_run("2. TECHNOLOGY STACK & ARCHITECTURE")
    run_s2.bold = True
    run_s2.font.size = Pt(12)
    run_s2.font.color.rgb = RGBColor(30, 58, 138)

    tech_rows = [
        ("Core Languages", ", ".join(tech_info.get("core_languages", [])) or "Modern polyglot stack"),
        ("Frontend & Apps", ", ".join(tech_info.get("frontend_and_apps", [])) or "Web standard frameworks"),
        ("Backend & Data Storage", ", ".join(tech_info.get("backend_and_data", [])) or "Distributed databases & messaging"),
        ("Cloud & Infrastructure", ", ".join(tech_info.get("cloud_and_infra", [])) or "Multi-cloud / container orchestration"),
        ("AI / ML & Tooling", ", ".join(tech_info.get("ai_and_ml", [])) or "LLM APIs & AI workflow engines"),
    ]

    table_tech = doc.add_table(rows=len(tech_rows), cols=2)
    table_tech.alignment = WD_TABLE_ALIGNMENT.CENTER
    for idx, (t_cat, t_tools) in enumerate(tech_rows):
        c0 = table_tech.cell(idx, 0)
        c1 = table_tech.cell(idx, 1)
        c0.width = Inches(2.5)
        c1.width = Inches(4.5)
        _set_cell_background(c0, "F8FAFC" if idx % 2 == 0 else "FFFFFF")
        _set_cell_background(c1, "F8FAFC" if idx % 2 == 0 else "FFFFFF")
        _set_cell_margins(c0, top=70, bottom=70, left=120, right=120)
        _set_cell_margins(c1, top=70, bottom=70, left=120, right=120)

        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_before = Pt(2)
        p0.paragraph_format.space_after = Pt(2)
        r0 = p0.add_run(t_cat)
        r0.bold = True
        r0.font.size = Pt(9.5)
        r0.font.color.rgb = RGBColor(71, 85, 105)

        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_before = Pt(2)
        p1.paragraph_format.space_after = Pt(2)
        r1 = p1.add_run(t_tools)
        r1.font.size = Pt(9.5)
        r1.font.color.rgb = RGBColor(15, 23, 42)

    # 5. Section 3: Engineering Culture & Leadership
    p_s3 = doc.add_paragraph()
    p_s3.paragraph_format.space_before = Pt(12)
    p_s3.paragraph_format.space_after = Pt(4)
    run_s3 = p_s3.add_run("3. ENGINEERING CULTURE & LEADERSHIP")
    run_s3.bold = True
    run_s3.font.size = Pt(12)
    run_s3.font.color.rgb = RGBColor(30, 58, 138)

    # Culture attributes
    p_cult_attr = doc.add_paragraph()
    p_cult_attr.paragraph_format.space_before = Pt(2)
    p_cult_attr.paragraph_format.space_after = Pt(2)
    _add_formatted_runs_docx(p_cult_attr, f"• **Operating Style:** {culture_info.get('style', 'Autonomous, high-velocity')}")

    p_rem = doc.add_paragraph()
    p_rem.paragraph_format.space_before = Pt(2)
    p_rem.paragraph_format.space_after = Pt(2)
    _add_formatted_runs_docx(p_rem, f"• **Remote Policy:** {culture_info.get('remote_policy', 'Distributed / Remote-first')}")

    p_rel = doc.add_paragraph()
    p_rel.paragraph_format.space_before = Pt(2)
    p_rel.paragraph_format.space_after = Pt(4)
    _add_formatted_runs_docx(p_rel, f"• **Release Cadence:** {culture_info.get('release_frequency', 'Continuous deployment')}")

    for h in culture_info.get("highlights", []):
        p_h = doc.add_paragraph(style="List Bullet")
        p_h.paragraph_format.space_before = Pt(0)
        p_h.paragraph_format.space_after = Pt(2)
        _add_formatted_runs_docx(p_h, h)

    # Leadership team
    if leaders:
        p_lead = doc.add_paragraph()
        p_lead.paragraph_format.space_before = Pt(6)
        p_lead.paragraph_format.space_after = Pt(2)
        r_lead = p_lead.add_run("Key Leadership Team:")
        r_lead.bold = True
        r_lead.font.size = Pt(10)
        r_lead.font.color.rgb = RGBColor(30, 58, 138)

        for l in leaders:
            p_l = doc.add_paragraph(style="List Bullet")
            p_l.paragraph_format.space_before = Pt(0)
            p_l.paragraph_format.space_after = Pt(2)
            _add_formatted_runs_docx(p_l, f"**{l.get('role', 'Executive')}:** {l.get('name', 'N/A')}")

    # Culture Sentiment
    if sentiment:
        p_sent = doc.add_paragraph()
        p_sent.paragraph_format.space_before = Pt(8)
        p_sent.paragraph_format.space_after = Pt(2)
        r_sent = p_sent.add_run(f"Culture & Employee Sentiment ({sentiment.get('overall_rating', '4.5/5.0')}):")
        r_sent.bold = True
        r_sent.font.size = Pt(10)
        r_sent.font.color.rgb = RGBColor(30, 58, 138)

        for pro in sentiment.get("pros", []):
            p_p = doc.add_paragraph(style="List Bullet")
            p_p.paragraph_format.space_before = Pt(0)
            p_p.paragraph_format.space_after = Pt(2)
            _add_formatted_runs_docx(p_p, f"**Strength:** {pro}")

        for con in sentiment.get("watch_outs", []):
            p_c = doc.add_paragraph(style="List Bullet")
            p_c.paragraph_format.space_before = Pt(0)
            p_c.paragraph_format.space_after = Pt(2)
            _add_formatted_runs_docx(p_c, f"**Trade-off:** {con}")

    # 6. Section 4: Recent Momentum & Milestones
    if momentum:
        p_s4 = doc.add_paragraph()
        p_s4.paragraph_format.space_before = Pt(12)
        p_s4.paragraph_format.space_after = Pt(4)
        run_s4 = p_s4.add_run("4. RECENT MOMENTUM & MILESTONES")
        run_s4.bold = True
        run_s4.font.size = Pt(12)
        run_s4.font.color.rgb = RGBColor(30, 58, 138)

        for m in momentum:
            p_m = doc.add_paragraph(style="List Bullet")
            p_m.paragraph_format.space_before = Pt(0)
            p_m.paragraph_format.space_after = Pt(2)
            _add_formatted_runs_docx(p_m, m)

    # 7. Section 5: Strategic Interview Questions & Talking Points
    if questions:
        p_s5 = doc.add_paragraph()
        p_s5.paragraph_format.space_before = Pt(12)
        p_s5.paragraph_format.space_after = Pt(4)
        run_s5 = p_s5.add_run("5. STRATEGIC INTERVIEW QUESTIONS TO ASK")
        run_s5.bold = True
        run_s5.font.size = Pt(12)
        run_s5.font.color.rgb = RGBColor(30, 58, 138)

        p_note = doc.add_paragraph()
        p_note.paragraph_format.space_before = Pt(0)
        p_note.paragraph_format.space_after = Pt(6)
        r_note = p_note.add_run("Pro-Tip: Grounding your interview inquiries in their specific architecture and recent milestones signals senior acumen and separates you from other candidates.")
        r_note.italic = True
        r_note.font.size = Pt(9)
        r_note.font.color.rgb = RGBColor(100, 116, 139)

        for idx, q in enumerate(questions, 1):
            table_q = doc.add_table(rows=1, cols=1)
            table_q.alignment = WD_TABLE_ALIGNMENT.CENTER
            c_q = table_q.cell(0, 0)
            c_q.width = Inches(7.0)
            _set_cell_background(c_q, "F8FAFC")
            _set_cell_margins(c_q, top=100, bottom=100, left=140, right=140)

            pq = c_q.paragraphs[0]
            pq.paragraph_format.space_before = Pt(2)
            pq.paragraph_format.space_after = Pt(2)
            rq_lbl = pq.add_run(f"Question #{idx}:\n")
            rq_lbl.bold = True
            rq_lbl.font.size = Pt(9.5)
            rq_lbl.font.color.rgb = RGBColor(37, 99, 235)  # Blue #2563eb

            rq_txt = pq.add_run(f'"{q}"')
            rq_txt.font.size = Pt(10)
            rq_txt.font.color.rgb = RGBColor(15, 23, 42)

            p_sp = doc.add_paragraph()
            p_sp.paragraph_format.space_before = Pt(2)
            p_sp.paragraph_format.space_after = Pt(2)

    # Save to in-memory buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def build_dossier_pdf(dossier_data: dict) -> io.BytesIO:
    """
    Generates an executive-grade PDF document from structured company dossier data.
    
    Includes:
    - Executive title banner & corporate identity header
    - Formatted executive summary callout block
    - Business model, funding rounds & valuation metrics
    - Technology stack & infrastructure breakdown
    - Culture, leadership & sentiment analysis
    - Strategic interview talking points & questions
    
    Returns an in-memory BytesIO stream ready for direct Streamlit download.
    """
    data = dossier_data or {}
    company_name = data.get("company_name") or "Target Employer"
    stage_info = data.get("stage_and_funding") or {}
    tech_info = data.get("tech_stack") or {}
    culture_info = data.get("engineering_culture") or {}
    leaders = data.get("leadership_team") or []
    momentum = data.get("recent_momentum") or []
    questions = data.get("strategic_interview_questions") or []
    sentiment = data.get("culture_and_sentiment") or {}
    ats_system = data.get("ats_system") or "Ashby / Greenhouse"
    summary_text = data.get("summary") or f"{company_name} corporate profile and strategic intelligence briefing."

    pdf = DossierPDF(company_name=company_name)
    pdf.set_title(f"Company Intelligence Dossier - {company_name}")
    pdf.set_author("Hyrd Multi-Agent Career Platform")
    pdf.set_creator("Hyrd Document Systems")
    pdf.add_page()

    # 1. Main Header Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(30, 58, 138)  # Deep Navy #1e3a8a
    pdf.cell(0, 7, f"COMPANY INTELLIGENCE DOSSIER", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(15, 23, 42)  # Dark slate #0f172a
    pdf.cell(0, 6, sanitize_text_for_pdf(company_name), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 116, 139)  # Slate #64748b
    sub_meta = f"Stage: {stage_info.get('stage', 'Growth Stage')}   |   ATS System: {ats_system}"
    pdf.cell(0, 5, sanitize_text_for_pdf(sub_meta), new_x="LMARGIN", new_y="NEXT")

    # Header divider rule
    pdf.ln(1)
    y = pdf.get_y()
    pdf.set_draw_color(30, 58, 138)
    pdf.set_line_width(0.6)
    pdf.line(18, y, 192, y)
    pdf.ln(3)

    # 2. Executive Summary Callout Box
    pdf.set_fill_color(241, 245, 249)  # Light slate #f1f5f9
    pdf.set_draw_color(203, 213, 225)
    pdf.set_line_width(0.3)
    
    clean_summary = sanitize_text_for_pdf(summary_text)
    box_w = 174
    
    # Calculate box height
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(box_w, 5, "EXECUTIVE SUMMARY:", fill=True, border="LTR", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(30, 41, 59)
    pdf.multi_cell(box_w, 4.8, clean_summary, fill=True, border="LBR")
    pdf.ln(3)

    # 3. Section 1: Business Model & Financial Overview
    pdf.draw_section_heading("1. Business Model & Financial Overview")
    pdf.draw_key_metric_row(
        "Funding Stage", str(stage_info.get("stage", "Private / Growth")),
        "Valuation / Market Cap", str(stage_info.get("valuation", "N/A"))
    )
    pdf.draw_key_metric_row(
        "Total Capital Raised", str(stage_info.get("total_raised", "N/A")),
        "Headcount & Scale", str(stage_info.get("headcount", "50 - 500+ employees"))
    )

    investors = stage_info.get("notable_investors") or []
    if investors:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(40, 4.5, "NOTABLE INVESTORS:", new_x="RIGHT", new_y="TOP")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(15, 23, 42)
        pdf.multi_cell(0, 4.5, sanitize_text_for_pdf(", ".join(investors)))
        pdf.ln(1)

    # 4. Section 2: Technology Stack & Engineering Architecture
    pdf.draw_section_heading("2. Technology Stack & Architecture")
    
    tech_categories = [
        ("Core Languages", ", ".join(tech_info.get("core_languages", [])) or "Modern polyglot stack"),
        ("Frontend & Apps", ", ".join(tech_info.get("frontend_and_apps", [])) or "Web standard frameworks"),
        ("Backend & Data", ", ".join(tech_info.get("backend_and_data", [])) or "Distributed databases & messaging"),
        ("Cloud & Infra", ", ".join(tech_info.get("cloud_and_infra", [])) or "Multi-cloud / container orchestration"),
        ("AI / ML Tooling", ", ".join(tech_info.get("ai_and_ml", [])) or "LLM APIs & AI workflow engines"),
    ]

    for cat_label, cat_tools in tech_categories:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(42, 5, sanitize_text_for_pdf(cat_label + ":"), new_x="RIGHT", new_y="TOP")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(15, 23, 42)
        pdf.multi_cell(0, 5, sanitize_text_for_pdf(cat_tools))
        pdf.ln(0.5)

    # 5. Section 3: Engineering Culture, Leadership & Sentiment
    pdf.draw_section_heading("3. Culture, Leadership & Environment")
    
    pdf.draw_bullet(f"Operating Style: {culture_info.get('style', 'Autonomous, high-velocity')}")
    pdf.draw_bullet(f"Remote Policy: {culture_info.get('remote_policy', 'Distributed / Remote-first')}")
    pdf.draw_bullet(f"Release Cadence: {culture_info.get('release_frequency', 'Continuous deployment')}")

    for h in culture_info.get("highlights", []):
        pdf.draw_bullet(h, prefix="*")

    if leaders:
        pdf.ln(1)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(30, 58, 138)
        pdf.cell(0, 4.5, "KEY LEADERSHIP TEAM:", new_x="LMARGIN", new_y="NEXT")
        for l in leaders:
            pdf.draw_bullet(f"{l.get('role', 'Executive')}: {l.get('name', 'N/A')}", prefix="-")

    if sentiment:
        pdf.ln(1)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(30, 58, 138)
        pdf.cell(0, 4.5, f"EMPLOYEE SENTIMENT ({sentiment.get('overall_rating', '4.5/5.0')}):", new_x="LMARGIN", new_y="NEXT")
        for pro in sentiment.get("pros", []):
            pdf.draw_bullet(f"Strength: {pro}", prefix="+")
        for con in sentiment.get("watch_outs", []):
            pdf.draw_bullet(f"Trade-off: {con}", prefix="!")

    # 6. Section 4: Recent Momentum & Milestones
    if momentum:
        pdf.draw_section_heading("4. Recent Momentum & Milestones")
        for m in momentum:
            pdf.draw_bullet(m, prefix="*")

    # 7. Section 5: Strategic Interview Questions
    if questions:
        pdf.draw_section_heading("5. Strategic Interview Questions to Ask")
        pdf.set_font("Helvetica", "I", 8.5)
        pdf.set_text_color(100, 116, 139)
        pdf.multi_cell(0, 4, "Grounding questions in company architecture and momentum demonstrates senior strategic caliber.")
        pdf.ln(2)

        for idx, q in enumerate(questions, 1):
            pdf.set_fill_color(248, 250, 252)
            pdf.set_draw_color(203, 213, 225)
            
            # Header line for question
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(37, 99, 235)  # Blue #2563eb
            pdf.cell(box_w, 4.5, f" Question #{idx}", fill=True, border="LTR", new_x="LMARGIN", new_y="NEXT")
            
            # Body of question
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(15, 23, 42)
            clean_q = f'"{sanitize_text_for_pdf(q)}"'
            pdf.multi_cell(box_w, 4.5, clean_q, fill=True, border="LBR")
            pdf.ln(2)

    # Save to buffer
    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer
