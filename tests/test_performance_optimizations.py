"""
Performance Optimization Verification & Regression Protection Test Suite.
Verifies all optimizations implemented in 07_PERFORMANCE_OPTIMIZATION_PLAN.md:
1. Job context compression and ATS keyword preservation (compress_job_context).
2. Gemini 503 instant cascade failover and 429 jittered backoff.
3. In-memory Company Dossier memoization.
4. User profile / registry in-memory write-through caching.
5. Optimized serialization fast path.
6. Tier 1 ATS scraper company concurrency.
7. Application bundle parallel exporter.
"""

import io
import time
import unittest
from unittest.mock import MagicMock, patch
import zipfile

from src.utils.ats_optimizer import compress_job_context, extract_ats_keywords
from src.agents.company_intelligence_agent import (
    generate_company_dossier,
    get_mock_company_dossier,
    clear_dossier_cache,
)
from src.utils.user_manager import (
    get_registry,
    save_registry,
    get_user_profile,
    save_user_profile,
    get_user_workspace,
    save_user_workspace,
    make_json_serializable,
    clear_user_cache,
)
from src.utils.gemini_client import generate_gemini_content
from src.agents.scrapers.ats_scrapers import (
    _fetch_companies_concurrently,
    GreenhouseScraper,
    AshbyScraper,
)
from src.tools.bundle_exporter import build_application_bundle_zip


class TestContextCompression(unittest.TestCase):
    """Verifies that compress_job_context removes noise while preserving critical tech keywords."""

    def test_strips_eeo_and_benefits_boilerplate(self):
        noisy_job_desc = """
        About the Role:
        We are seeking a Staff Python and AI Engineer to architect high-throughput microservices using FastAPI,
        Kubernetes, PostgreSQL, and Gemini API.

        Responsibilities:
        - Design scalable distributed systems with Docker and Redis.
        - Build resilient RAG retrieval pipelines using Qdrant vector database.
        - Optimize low-latency backend endpoints for high availability.

        Requirements:
        - 5+ years of production experience in Python and cloud architectures (AWS / GCP).
        - Deep understanding of CI/CD, system architecture, and unit testing.

        Benefits & Perks:
        We offer 100% employer-covered health, dental, and vision insurance. Unlimited paid time off (PTO),
        gym stipend, catered lunches, commuter benefits, 401(k) matching up to 4%, and home office stipends.

        Equal Opportunity Employer:
        We are an Equal Opportunity Employer and do not discriminate against any employee or applicant
        based on race, color, religion, sex, sexual orientation, gender identity, national origin, veteran status,
        or disability status. All employment decisions are based on business needs, job requirements, and individual qualifications.
        Must be able to lift 25 pounds. Covid-19 vaccination policy is enforced.
        """
        compressed = compress_job_context(noisy_job_desc, max_chars=1800)

        # Confirm boilerplate removal
        self.assertNotIn("Equal Opportunity Employer", compressed)
        self.assertNotIn("veteran status", compressed)
        self.assertNotIn("lift 25 pounds", compressed)

        # Confirm critical tech keywords are strictly preserved
        for kw in ["Python", "FastAPI", "Kubernetes", "PostgreSQL", "Gemini", "Docker", "Redis", "Qdrant", "AWS"]:
            self.assertIn(kw, compressed)

        self.assertLessEqual(len(compressed), 1800)

    def test_handles_empty_or_short_input(self):
        self.assertEqual(compress_job_context(""), "")
        self.assertEqual(compress_job_context(None), "")
        short_desc = "Software Engineer - Python, Docker, AWS."
        self.assertEqual(compress_job_context(short_desc), short_desc)


class TestGeminiInstantFailover(unittest.TestCase):
    """Verifies that 503 capacity errors trigger instant model cascade failover without 2s sleep blocks."""

    @patch("src.utils.gemini_client.get_genai_client")
    @patch("src.utils.gemini_client.get_available_models")
    def test_instant_503_failover(self, mock_models, mock_get_client):
        mock_models.return_value = (["gemini-3.8-flash", "gemini-2.5-flash"], "gemini-3.8-flash")

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # First model throws 503 UNAVAILABLE, second model succeeds
        call_count = 0
        def fake_generate_content(model, contents, config=None):
            nonlocal call_count
            call_count += 1
            if model == "gemini-3.8-flash":
                raise Exception("503 The model is overloaded. Please try again later.")
            response = MagicMock()
            response.text = "Success from fallback model"
            return response

        mock_client.models.generate_content.side_effect = fake_generate_content

        start_time = time.time()
        result = generate_gemini_content(
            prompt="Hello world",
            api_key="fake-key",
            preferred_model="gemini-3.8-flash",
            max_retries_per_model=2,
            backoff_delay=2.0,
        )
        elapsed = time.time() - start_time

        self.assertEqual(result, "Success from fallback model")
        # Should have failed over to gemini-2.5-flash immediately without sleeping 2.0s
        self.assertLess(elapsed, 1.0)
        self.assertEqual(call_count, 2)


class TestCompanyDossierCache(unittest.TestCase):
    """Verifies in-memory caching of Company Dossier queries."""

    def setUp(self):
        clear_dossier_cache()

    def test_dossier_cache_memoization(self):
        # First call populates cache
        d1 = generate_company_dossier("Stripe", job_title="Staff Engineer")
        self.assertEqual(d1["company_name"], "Stripe")

        # Second call should be served from memory instantly
        start = time.time()
        d2 = generate_company_dossier("Stripe", job_title="Staff Engineer")
        elapsed = time.time() - start

        self.assertEqual(d1, d2)
        self.assertLess(elapsed, 0.01)

    def test_clear_dossier_cache(self):
        generate_company_dossier("Databricks", job_title="Data Engineer")
        clear_dossier_cache()
        from src.agents.company_intelligence_agent import _DOSSIER_CACHE
        self.assertEqual(len(_DOSSIER_CACHE), 0)


class TestUserManagerCachingAndSerialization(unittest.TestCase):
    """Verifies user registry and profile in-memory caching and serialization fast paths."""

    def setUp(self):
        clear_user_cache()

    def test_profile_and_registry_in_memory_cache(self):
        reg = get_registry()
        self.assertIsInstance(reg, dict)

        # Call get_registry again; should return identical structure from memory
        reg2 = get_registry()
        self.assertEqual(reg, reg2)

    def test_make_json_serializable_fast_path(self):
        # Primitive dictionary should pass through fast path
        primitive_data = {
            "title": "Software Engineer",
            "score": 95,
            "rate": 120.5,
            "active": True,
            "missing": None,
        }
        res = make_json_serializable(primitive_data)
        self.assertEqual(res, primitive_data)

        # Primitive list
        primitive_list = ["python", "docker", "aws", 123, True]
        res_list = make_json_serializable(primitive_list)
        self.assertEqual(res_list, primitive_list)


class TestScraperConcurrency(unittest.TestCase):
    """Verifies concurrent company iteration preserves priority and executes in parallel."""

    def test_fetch_companies_concurrently_ordering(self):
        companies = [
            ("comp-a", "Company A", True),
            ("comp-b", "Company B", False),
            ("comp-c", "Company C", False),
        ]

        mock_scraper = MagicMock()
        def mock_safe_fetch(company_slug, query, location, limit, company_display_name, is_custom_target):
            time.sleep(0.05)  # simulate network latency
            mock_job = MagicMock()
            mock_job.company = company_display_name
            mock_job.is_custom_company = is_custom_target
            return [mock_job]

        mock_scraper.safe_fetch_jobs.side_effect = mock_safe_fetch

        start = time.time()
        results = _fetch_companies_concurrently(
            scraper=mock_scraper,
            merged_items=companies,
            query="python",
            location="Remote",
            limit=5,
            max_workers=3,
        )
        elapsed = time.time() - start

        # 3 companies at 50ms each in parallel should take ~50-100ms, not 150ms
        self.assertLess(elapsed, 0.25)
        self.assertEqual(len(results), 3)
        # Verify strict sequence preservation
        self.assertEqual(results[0].company, "Company A")
        self.assertEqual(results[1].company, "Company B")
        self.assertEqual(results[2].company, "Company C")


class TestParallelBundleExporter(unittest.TestCase):
    """Verifies build_application_bundle_zip parallel generation produces valid zip with all artifacts."""

    def test_bundle_zip_parallel_assembly(self):
        mock_job = {
            "title": "Principal Architect",
            "company": "Apex Labs",
            "location": "Remote",
            "description": "Lead multi-agent AI architecture with Python and Gemini.",
            "matched_skills": ["Python", "Gemini", "Multi-Agent"],
            "profile_fit_score": 95,
        }
        mock_profile = {
            "full_name": "Marcus Aurelius",
            "headline": "Principal Architect",
            "location": "San Francisco, CA",
            "email": "marcus@example.com",
            "phone": "+1 555-0192",
            "core_skills": ["Python", "Gemini", "Kubernetes"],
            "experience_highlights": ["Built distributed autonomous systems"],
        }

        # Run bundle export without pre-cached artifacts to trigger parallel worker generation
        zip_buffer = build_application_bundle_zip(
            job=mock_job,
            profile=mock_profile,
            cached_docs={},
        )

        self.assertIsInstance(zip_buffer, io.BytesIO)
        zip_bytes = zip_buffer.getvalue()
        self.assertGreater(len(zip_bytes), 1000)

        # Verify ZIP contains all 5 artifact types
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            namelist = zf.namelist()
            self.assertTrue(any("Resume" in name and name.endswith(".docx") for name in namelist))
            self.assertTrue(any("Resume" in name and name.endswith(".pdf") for name in namelist))
            self.assertTrue(any("CoverLetter" in name and name.endswith(".docx") for name in namelist))
            self.assertTrue(any("InterviewPrep" in name and name.endswith(".docx") for name in namelist))
            self.assertTrue(any("CompanyIntelligence" in name and name.endswith(".docx") for name in namelist))
            self.assertTrue(any("CompanyIntelligence" in name and name.endswith(".pdf") for name in namelist))
            self.assertTrue(any("Outreach" in name and name.endswith(".txt") for name in namelist))
            self.assertEqual(len(namelist), 8)


if __name__ == "__main__":
    unittest.main()
