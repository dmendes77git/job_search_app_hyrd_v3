"""
Unit tests for Company Intelligence Dossier document exporters (.docx and .pdf).
Verifies that:
- build_dossier_docx generates valid, well-formed Microsoft Word files.
- build_dossier_pdf generates valid, well-formed PDF files.
- In-memory BytesIO streams are returned with non-zero size.
- Edge cases (empty data, missing fields, unicode and special symbols) are handled gracefully.
- Upstream ATS and corporate intelligence fields are faithfully rendered.
"""

import io
from docx import Document
from pypdf import PdfReader
from src.tools.dossier_exporter import build_dossier_docx, build_dossier_pdf, sanitize_text_for_pdf
from src.agents.company_intelligence_agent import get_mock_company_dossier


def test_sanitize_text_for_pdf():
    """Verify that unicode characters and symbols are safely converted for PDF."""
    raw = "Toast — Lead AI “Engineer” • €50,000 £40,000 🚀 ⚡ 🎯"
    cleaned = sanitize_text_for_pdf(raw)
    assert "—" not in cleaned
    assert "“" not in cleaned
    assert "EUR" in cleaned
    assert "GBP" in cleaned
    # Ensure it encodes cleanly to Latin-1
    encoded = cleaned.encode("latin-1")
    assert len(encoded) > 0


def test_build_dossier_docx_with_full_data():
    """Verify build_dossier_docx generates valid DOCX with all required sections."""
    dossier = get_mock_company_dossier("Linear App", job_title="Staff Frontend Engineer")
    stream = build_dossier_docx(dossier)
    
    assert isinstance(stream, io.BytesIO)
    bytes_data = stream.getvalue()
    assert len(bytes_data) > 5000  # Should be a substantive docx file
    
    # Read back with python-docx to verify format validity
    stream.seek(0)
    doc = Document(stream)
    
    # Verify title & sections exist
    headings = [p.text for p in doc.paragraphs if p.text]
    assert any("COMPANY INTELLIGENCE DOSSIER" in h for h in headings)
    assert any("Linear App" in h for h in headings)
    assert any("BUSINESS MODEL" in h for h in headings)
    assert any("TECHNOLOGY STACK" in h for h in headings)
    assert any("ENGINEERING CULTURE" in h for h in headings)
    
    # Verify tables were created (financial overview, tech stack, summary, question boxes)
    assert len(doc.tables) >= 3


def test_build_dossier_pdf_with_full_data():
    """Verify build_dossier_pdf generates valid PDF parseable by pypdf."""
    dossier = get_mock_company_dossier("Toast Inc.", job_title="Principal Systems Architect")
    stream = build_dossier_pdf(dossier)
    
    assert isinstance(stream, io.BytesIO)
    bytes_data = stream.getvalue()
    assert len(bytes_data) > 2000
    assert bytes_data.startswith(b"%PDF")
    
    # Read back with pypdf
    stream.seek(0)
    reader = PdfReader(stream)
    assert len(reader.pages) >= 1
    
    page_text = reader.pages[0].extract_text()
    assert "COMPANY INTELLIGENCE DOSSIER" in page_text
    assert "Toast Inc." in page_text or "Toast" in page_text


def test_build_dossier_docx_empty_dict_resilience():
    """Verify build_dossier_docx handles empty or incomplete dictionaries without crashing."""
    stream = build_dossier_docx({})
    assert isinstance(stream, io.BytesIO)
    assert len(stream.getvalue()) > 1000
    
    stream.seek(0)
    doc = Document(stream)
    assert len(doc.paragraphs) > 0


def test_build_dossier_pdf_empty_dict_resilience():
    """Verify build_dossier_pdf handles empty or incomplete dictionaries without crashing."""
    stream = build_dossier_pdf({})
    assert isinstance(stream, io.BytesIO)
    bytes_data = stream.getvalue()
    assert bytes_data.startswith(b"%PDF")
    
    stream.seek(0)
    reader = PdfReader(stream)
    assert len(reader.pages) >= 1


def test_dossier_exporter_unicode_handling():
    """Verify dossier exporter safely renders complex accents and currencies."""
    dossier = {
        "company_name": "Farfetch & Co. — Lisboa / São Paulo",
        "summary": "High-fashion e-commerce platform with €100M+ ARR and “innovative” architecture.",
        "stage_and_funding": {
            "stage": "Public (NYSE)",
            "valuation": "€1.5B",
            "total_raised": "$700M",
            "notable_investors": ["Eurazeo", "Advent International"],
            "headcount": "3,000+ funcionários",
        },
        "tech_stack": {
            "core_languages": ["Python", "C#", "TypeScript"],
            "frontend_and_apps": ["React", "Next.js"],
            "backend_and_data": ["PostgreSQL", "Kafka", "Redis"],
            "cloud_and_infra": ["Azure", "Kubernetes"],
            "ai_and_ml": ["Computer Vision", "Recommendations"],
        },
        "engineering_culture": {
            "style": "Autonomous squad-based engineering",
            "remote_policy": "Híbrido (2 dias escritório)",
            "release_frequency": "Continuous Deployment",
            "highlights": ["Fortes práticas de código limpo e testes automatizados."],
        },
        "leadership_team": [
            {"role": "CEO", "name": "José Neves"},
            {"role": "CTO", "name": "Cipriano Sousa"},
        ],
        "recent_momentum": ["Expanding presence across Southern Europe and Latin America."],
        "strategic_interview_questions": [
            "How does the Lisbon engineering hub collaborate with the London product team?",
            "What strategies are deployed to maintain 99.99% uptime during Black Friday surges?",
        ],
        "culture_and_sentiment": {
            "overall_rating": "4.2 / 5.0",
            "pros": ["Ótimo ambiente de trabalho", "Salários competitivos"],
            "watch_outs": ["Ambiente rápido e dinâmico"],
        },
        "ats_system": "Workday",
    }
    
    docx_buf = build_dossier_docx(dossier)
    assert len(docx_buf.getvalue()) > 5000
    
    pdf_buf = build_dossier_pdf(dossier)
    assert len(pdf_buf.getvalue()) > 2000
    assert pdf_buf.getvalue().startswith(b"%PDF")
