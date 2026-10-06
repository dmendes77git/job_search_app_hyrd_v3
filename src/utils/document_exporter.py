"""
ATS-Certified Document Exporter for Resumes and Cover Letters.
Generates 100% ATS parser-compliant PDF and Microsoft Word (.docx) files.
Adheres strictly to modern ATS parsing standards:
- Single-column flow (no floating text boxes, multi-column tables, or graphics)
- Standard typography (Helvetica for PDF, Calibri for DOCX)
- Clear heading hierarchy recognized by Greenhouse, Ashby, Lever, Workday
- Fully machine-readable text streams with UTF-8 / Latin-1 safe encoding
"""

import io
import re
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from fpdf import FPDF


def sanitize_text_for_pdf(text: str) -> str:
    """Sanitize unicode characters to ensure standard PDF font encoding compatibility."""
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
        "⚡": "*",
        "🎯": "*",
        "💼": "*",
        "🏢": "*",
        "🛡️": "*",
        "✨": "*",
        "→": "->",
        "←": "<-",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Strip any characters outside Latin-1 / standard ASCII that could crash fpdf default fonts
    return text.encode("latin-1", "replace").decode("latin-1")


class ATSResumePDF(FPDF):
    """Custom FPDF class tailored for ATS parser friendliness and crisp visual layout."""

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=16)
        self.set_margins(left=18, top=16, right=18)

    def draw_section_heading(self, title: str):
        """Render a clean standard section header with subtle baseline rule."""
        self.ln(3)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(30, 58, 138)  # Deep Navy #1e3a8a
        self.cell(0, 6, sanitize_text_for_pdf(title.upper()), new_x="LMARGIN", new_y="NEXT")
        
        # Subtle horizontal divider line
        y = self.get_y()
        self.set_draw_color(203, 213, 225)  # Light slate #cbd5e1
        self.set_line_width(0.3)
        self.line(18, y, 192, y)
        self.ln(2)

    def draw_role_heading(self, role_line: str, date_line: str = ""):
        """Render job title, company, and date line."""
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(15, 23, 42)  # Dark slate #0f172a
        
        if date_line:
            # Title & Company on left, Date on right
            clean_role = sanitize_text_for_pdf(role_line)
            clean_date = sanitize_text_for_pdf(date_line)
            
            # Print title
            self.cell(120, 5, clean_role, new_x="RIGHT", new_y="TOP")
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(100, 116, 139)  # Slate gray #64748b
            self.cell(0, 5, clean_date, align="R", new_x="LMARGIN", new_y="NEXT")
        else:
            self.cell(0, 5, sanitize_text_for_pdf(role_line), new_x="LMARGIN", new_y="NEXT")
        self.ln(0.5)

    def draw_bullet(self, text: str):
        """Render a clean bullet item with slight indentation."""
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(51, 65, 85)  # #334155
        
        indent = 4
        bullet_char = "-"
        
        # Bullet mark
        curr_x = self.get_x()
        curr_y = self.get_y()
        self.set_x(curr_x + indent)
        self.cell(4, 4.5, bullet_char, new_x="RIGHT", new_y="TOP")
        
        # Bullet text
        clean_text = sanitize_text_for_pdf(text)
        self.multi_cell(0, 4.5, clean_text)
        self.ln(1)

    def draw_body_paragraph(self, text: str):
        """Render regular text paragraph."""
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(51, 65, 85)
        clean_text = sanitize_text_for_pdf(text)
        self.multi_cell(0, 4.8, clean_text)
        self.ln(2)


def create_cv_pdf(cv_markdown: str, candidate_name: str = "Candidate") -> io.BytesIO:
    """
    Generate an ATS-certified PDF resume from markdown text using FPDF2.
    Adheres strictly to single-column, non-tabular formatting.
    """
    pdf = ATSResumePDF()
    pdf.set_title(f"Resume - {candidate_name}")
    pdf.set_author(candidate_name)
    pdf.set_creator("Hyrd (v3)")
    pdf.add_page()

    lines = cv_markdown.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Header 1: Candidate Name
        if line.startswith("# "):
            name_text = line[2:].strip()
            pdf.set_font("Helvetica", "B", 18)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(0, 8, sanitize_text_for_pdf(name_text), align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
            i += 1
            continue

        # Section Header: ## TITLE
        if line.startswith("## "):
            sec_title = line[3:].strip()
            pdf.draw_section_heading(sec_title)
            i += 1
            continue

        # Role Subheading: ### Role | Company
        if line.startswith("### "):
            role_text = line[4:].strip()
            # Check if next line is italics date or location e.g. *2021 - Present | Remote*
            date_line = ""
            if i + 1 < len(lines):
                next_l = lines[i + 1].strip()
                if (next_l.startswith("*") and next_l.endswith("*")) or (next_l.startswith("_") and next_l.endswith("_")):
                    date_line = next_l.strip("*_").strip()
                    i += 1
            pdf.draw_role_heading(role_text, date_line)
            i += 1
            continue

        # Bullet items: - or *
        if line.startswith("- ") or line.startswith("* "):
            bullet_text = line[2:].strip()
            # Clean any bold/italics markdown markers for smooth readable text in ATS
            clean_b = re.sub(r"\*\*(.*?)\*\*", r"\1", bullet_text)
            clean_b = re.sub(r"\*(.*?)\*", r"\1", clean_b)
            pdf.draw_bullet(clean_b)
            i += 1
            continue

        # Horizontal divider: ---
        if line.startswith("---"):
            i += 1
            continue

        # Standard Paragraph (e.g. contact line or summary block)
        clean_p = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
        clean_p = re.sub(r"\*(.*?)\*", r"\1", clean_p)
        
        # Check if it looks like a contact line (contains | or email/phone)
        if ("|" in clean_p or "@" in clean_p) and pdf.get_y() < 40:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(71, 85, 105)
            pdf.cell(0, 5, sanitize_text_for_pdf(clean_p), align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        else:
            pdf.draw_body_paragraph(clean_p)

        i += 1

    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer


def create_cv_docx(cv_markdown: str) -> io.BytesIO:
    """
    Generate an ATS-certified Microsoft Word (.docx) resume from markdown.
    Single-column, standard Calibri fonts, compliant with all ATS parsers.
    """
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.65)
        section.bottom_margin = Inches(0.65)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)

    # Set default font
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(10)
    normal_style.font.color.rgb = RGBColor(51, 65, 85)

    lines = cv_markdown.strip().split("\n")
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        if line_clean.startswith("# "):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(line_clean[2:])
            run.bold = True
            run.font.size = Pt(17)
            run.font.color.rgb = RGBColor(15, 23, 42)

        elif line_clean.startswith("## "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(3)
            run = p.add_run(line_clean[3:].upper())
            run.bold = True
            run.font.size = Pt(11.5)
            run.font.color.rgb = RGBColor(30, 58, 138)  # Deep Navy

        elif line_clean.startswith("### "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(1)
            run = p.add_run(line_clean[4:])
            run.bold = True
            run.font.size = Pt(10.5)
            run.font.color.rgb = RGBColor(30, 41, 59)

        elif line_clean.startswith("- ") or line_clean.startswith("* "):
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            _add_formatted_runs_docx(p, line_clean[2:])

        elif line_clean.startswith("---"):
            continue

        else:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.15
            if ("|" in line_clean or "@" in line_clean) and len(doc.paragraphs) <= 3:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _add_formatted_runs_docx(p, line_clean)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def create_cover_letter_pdf(
    letter_text: str,
    candidate_name: str = "Candidate",
    company: str = "Company",
    job_title: str = "Position",
) -> io.BytesIO:
    """
    Generate an executive, professional PDF cover letter.
    Formatted with clean letterhead, date, employer address block, and sign-off.
    """
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(left=22, top=20, right=22)
    pdf.set_title(f"Cover Letter - {candidate_name} for {company}")
    pdf.set_author(candidate_name)
    pdf.set_creator("Hyrd (v3)")
    pdf.add_page()

    # Executive Header
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, sanitize_text_for_pdf(candidate_name.upper()), new_x="LMARGIN", new_y="NEXT")

    # Sub-header divider
    y = pdf.get_y()
    pdf.set_draw_color(30, 58, 138)
    pdf.set_line_width(0.6)
    pdf.line(22, y, 188, y)
    pdf.ln(5)

    paragraphs = letter_text.strip().split("\n\n")
    for para in paragraphs:
        para_clean = para.strip()
        if not para_clean:
            continue

        # Check if header / subject line
        if para_clean.startswith("RE:") or para_clean.startswith("Subject:") or para_clean.startswith("**RE:"):
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(30, 58, 138)
            clean_sub = re.sub(r"\*\*(.*?)\*\*", r"\1", para_clean)
            pdf.multi_cell(0, 5, sanitize_text_for_pdf(clean_sub))
            pdf.ln(3)
        elif para_clean.startswith("# "):
            continue  # Skip raw markdown title if duplicated
        else:
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(51, 65, 85)
            clean_p = re.sub(r"\*\*(.*?)\*\*", r"\1", para_clean)
            clean_p = re.sub(r"\*(.*?)\*", r"\1", clean_p)
            pdf.multi_cell(0, 5.2, sanitize_text_for_pdf(clean_p))
            pdf.ln(3)

    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer


def create_cover_letter_docx(
    letter_text: str,
    candidate_name: str = "Candidate",
    company: str = "Company",
    job_title: str = "Position",
) -> io.BytesIO:
    """
    Generate a formatted Microsoft Word (.docx) cover letter.
    """
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.85)
        section.right_margin = Inches(0.85)

    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = RGBColor(51, 65, 85)

    # Name Header
    p_header = doc.add_paragraph()
    p_header.paragraph_format.space_before = Pt(0)
    p_header.paragraph_format.space_after = Pt(2)
    run_name = p_header.add_run(candidate_name)
    run_name.bold = True
    run_name.font.size = Pt(16)
    run_name.font.color.rgb = RGBColor(15, 23, 42)

    paragraphs = letter_text.strip().split("\n\n")
    for para in paragraphs:
        para_clean = para.strip()
        if not para_clean:
            continue
        if para_clean.startswith("# "):
            continue

        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.line_spacing = 1.15

        if para_clean.startswith("RE:") or para_clean.startswith("Subject:") or para_clean.startswith("**RE:"):
            run = p.add_run(re.sub(r"\*\*(.*?)\*\*", r"\1", para_clean))
            run.bold = True
            run.font.color.rgb = RGBColor(30, 58, 138)
        else:
            _add_formatted_runs_docx(p, para_clean)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def _add_formatted_runs_docx(paragraph, text: str) -> None:
    """Helper to parse bold (**...**) and italic (*...*) in text runs for python-docx."""
    parts = re.split(r"(\*\*.*?\*\*)", text)
    for part in parts:
        if part.startswith("**") and part.endswith("**") and len(part) >= 4:
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        else:
            sub_parts = re.split(r"(\*.*?\*)", part)
            for sp in sub_parts:
                if sp.startswith("*") and sp.endswith("*") and len(sp) >= 2:
                    run = paragraph.add_run(sp[1:-1])
                    run.italic = True
                else:
                    paragraph.add_run(sp)


# Canonical alias for Markdown run formatting in DOCX documents
_add_formatted_runs = _add_formatted_runs_docx


def create_interview_prep_docx(prep_pack: dict) -> io.BytesIO:
    """Generate a clean Microsoft Word (.docx) document for the Interview Prep Pack."""
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    raw_text = prep_pack.get("raw_markdown", "")
    lines = raw_text.splitlines()

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        if line_clean.startswith("# "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(line_clean[2:])
            run.bold = True
            run.font.size = Pt(17)
            run.font.color.rgb = RGBColor(15, 23, 42)

        elif line_clean.startswith("## "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(3)
            run = p.add_run(line_clean[3:])
            run.bold = True
            run.font.size = Pt(13)
            run.font.color.rgb = RGBColor(37, 99, 235)

        elif line_clean.startswith("### "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(line_clean[4:])
            run.bold = True
            run.font.size = Pt(11)
            run.font.color.rgb = RGBColor(30, 41, 59)

        elif line_clean.startswith("- ") or line_clean.startswith("* "):
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            _add_formatted_runs_docx(p, line_clean[2:])

        elif line_clean.startswith("---"):
            continue

        else:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.15
            _add_formatted_runs_docx(p, line_clean)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def create_outreach_docx(
    campaign: dict,
    candidate_name: str = "Candidate",
    company: str = "Target Company",
    job_title: str = "Target Role",
) -> io.BytesIO:
    """Generate a formatted Microsoft Word (.docx) document containing the complete outreach campaign."""
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Document Header
    p_header = doc.add_paragraph()
    p_header.paragraph_format.space_before = Pt(0)
    p_header.paragraph_format.space_after = Pt(2)
    run_h = p_header.add_run("Executive Recruiter Cold Outreach Campaign")
    run_h.bold = True
    run_h.font.size = Pt(18)
    run_h.font.color.rgb = RGBColor(15, 23, 42)

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(12)
    run_sub = p_sub.add_run(f"Candidate: {candidate_name}  |  Target Role: {job_title}  |  Employer: {company}")
    run_sub.font.size = Pt(10)
    run_sub.font.color.rgb = RGBColor(100, 116, 139)

    messages = [
        ("1. LinkedIn Connection Request Note (<= 300 Characters)", campaign.get("linkedin_note", {}).get("text", "") if isinstance(campaign.get("linkedin_note"), dict) else str(campaign.get("linkedin_note", "")), None, f"{campaign.get('linkedin_note', {}).get('char_count', 0) if isinstance(campaign.get('linkedin_note'), dict) else len(str(campaign.get('linkedin_note', '')))} / 300 Characters"),
        ("2. Hiring Manager Direct Cold Email", campaign.get("hiring_manager_email", {}).get("body", ""), campaign.get("hiring_manager_email", {}).get("subject", ""), f"{campaign.get('hiring_manager_email', {}).get('word_count', 0)} words"),
        ("3. Recruiter & Talent Acquisition InMail", campaign.get("recruiter_inmail", {}).get("body", ""), campaign.get("recruiter_inmail", {}).get("subject", ""), f"{campaign.get('recruiter_inmail', {}).get('word_count', 0)} words"),
        ("4. Warm Internal Referral / Insider Request", campaign.get("referral_request", {}).get("body", ""), campaign.get("referral_request", {}).get("subject", ""), f"{campaign.get('referral_request', {}).get('word_count', 0)} words"),
        ("5. Post-Interview Follow-Up & Thank You Note", campaign.get("thank_you_note", {}).get("body", ""), campaign.get("thank_you_note", {}).get("subject", ""), f"{campaign.get('thank_you_note', {}).get('word_count', 0)} words"),
    ]

    for title_text, body_text, subject_line, meta_badge in messages:
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(12)
        h.paragraph_format.space_after = Pt(2)
        run_h = h.add_run(title_text)
        run_h.bold = True
        run_h.font.size = Pt(12.5)
        run_h.font.color.rgb = RGBColor(37, 99, 235)

        if meta_badge:
            m = doc.add_paragraph()
            m.paragraph_format.space_before = Pt(0)
            m.paragraph_format.space_after = Pt(4)
            run_m = m.add_run(f"Budget / Length: {meta_badge}")
            run_m.italic = True
            run_m.font.size = Pt(9)
            run_m.font.color.rgb = RGBColor(100, 116, 139)

        if subject_line:
            p_s = doc.add_paragraph()
            p_s.paragraph_format.space_before = Pt(2)
            p_s.paragraph_format.space_after = Pt(4)
            run_sl = p_s.add_run("Subject Line: ")
            run_sl.bold = True
            run_sl.font.size = Pt(10.5)
            run_sv = p_s.add_run(subject_line)
            run_sv.font.size = Pt(10.5)
            run_sv.font.color.rgb = RGBColor(30, 41, 59)

        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = table.cell(0, 0)
        cell.width = Inches(7.0)

        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), 'F8FAFC')
        tcPr.append(shd)

        cell_p = cell.paragraphs[0]
        cell_p.paragraph_format.space_before = Pt(4)
        cell_p.paragraph_format.space_after = Pt(4)
        cell_p.paragraph_format.line_spacing = 1.15

        for b_line in str(body_text).splitlines():
            if b_line.strip():
                _add_formatted_runs_docx(cell_p, b_line)
                cell_p.add_run("\n")

        p_spacer = doc.add_paragraph()
        p_spacer.paragraph_format.space_before = Pt(4)
        p_spacer.paragraph_format.space_after = Pt(4)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
