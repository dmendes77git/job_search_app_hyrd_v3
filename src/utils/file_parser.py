"""
File Parser Utility: Extracts text from PDF, DOCX, and TXT resumes.
"""

import io
from typing import Optional
import pypdf
import docx


def extract_text_from_file(uploaded_file) -> str:
    """
    Extract readable text from an uploaded Streamlit file buffer (.pdf, .docx, .txt).
    Returns clean, normalized string.
    """
    if uploaded_file is None:
        return ""

    file_name = uploaded_file.name.lower()
    file_bytes = uploaded_file.getvalue()

    if file_name.endswith(".pdf"):
        return _extract_pdf(file_bytes)
    elif file_name.endswith(".docx"):
        return _extract_docx(file_bytes)
    elif file_name.endswith(".txt") or file_name.endswith(".md"):
        return _extract_txt(file_bytes)
    else:
        raise ValueError(f"Unsupported file format: {file_name}. Please upload a .pdf, .docx, .txt, or .md file.")


def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using pypdf."""
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    extracted_pages = []

    for idx, page in enumerate(reader.pages):
        page_text = page.extract_text()
        if page_text:
            extracted_pages.append(page_text.strip())

    if not extracted_pages:
        raise ValueError("Could not extract any readable text from this PDF. It may be an image scan or password-protected.")

    return "\n\n".join(extracted_pages)


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    doc = docx.Document(io.BytesIO(file_bytes))
    paragraphs = []

    for p in doc.paragraphs:
        text = p.text.strip()
        if text:
            paragraphs.append(text)

    # Also extract any text inside tables
    for table in doc.tables:
        for row in table.rows:
            row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_text:
                paragraphs.append(" | ".join(row_text))

    if not paragraphs:
        raise ValueError("No readable text found in this DOCX file.")

    return "\n\n".join(paragraphs)


def _extract_txt(file_bytes: bytes) -> str:
    """Decode text bytes using UTF-8 or Latin-1."""
    try:
        return file_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1", errors="ignore").strip()


def normalize_resume_sections(text: str) -> dict:
    """
    Parse unstructured or markdown resume text into standardized semantic sections:
    summary, skills, experience, education, projects, certifications, other.
    """
    if not text:
        return {
            "summary": "",
            "skills": "",
            "experience": "",
            "education": "",
            "projects": "",
            "certifications": "",
            "raw": "",
        }

    lines = text.split("\n")
    sections = {
        "summary": [],
        "skills": [],
        "experience": [],
        "education": [],
        "projects": [],
        "certifications": [],
        "header": [],
        "other": [],
    }

    current_sec = "header"

    def match_heading(line_clean: str) -> Optional[str]:
        l = line_clean.strip("#*-: \t").lower()
        if not l or len(l) > 40:
            return None
        if any(k in l for k in ["summary", "profile", "about me", "objective", "executive"]):
            return "summary"
        if any(k in l for k in ["skill", "competenc", "stack", "technolog", "proficienc"]):
            return "skills"
        if any(k in l for k in ["experience", "employment", "work history", "career", "professional background"]):
            return "experience"
        if any(k in l for k in ["education", "academic", "degree", "university"]):
            return "education"
        if any(k in l for k in ["project", "open source", "portfolio"]):
            return "projects"
        if any(k in l for k in ["certificat", "license", "credential", "award"]):
            return "certifications"
        return None

    for line in lines:
        detected = match_heading(line)
        if detected:
            current_sec = detected
            continue
        sections[current_sec].append(line)

    return {
        "summary": "\n".join(sections["summary"]).strip(),
        "skills": "\n".join(sections["skills"]).strip(),
        "experience": "\n".join(sections["experience"]).strip(),
        "education": "\n".join(sections["education"]).strip(),
        "projects": "\n".join(sections["projects"]).strip(),
        "certifications": "\n".join(sections["certifications"]).strip(),
        "raw": text.strip(),
    }

