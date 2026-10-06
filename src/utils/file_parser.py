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
    elif file_name.endswith(".txt"):
        return _extract_txt(file_bytes)
    else:
        raise ValueError(f"Unsupported file format: {file_name}. Please upload a .pdf, .docx, or .txt file.")


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
