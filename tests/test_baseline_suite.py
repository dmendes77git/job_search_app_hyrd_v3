"""
Comprehensive Baseline Test Suite for Hyrd (v3).
Protects all existing agentic capabilities, utilities, and core data workflows
prior to architectural refactoring. Ensures ZERO regressions across the entire platform.
"""

import os
import sys
import io
import unittest
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestAtsOptimizer(unittest.TestCase):
    """Verifies ATS keyword extraction and compatibility audits."""

    def setUp(self):
        from src.utils.ats_optimizer import (
            extract_ats_keywords,
            format_ats_contact_block,
            audit_ats_cv_compatibility,
        )
        self.extract_ats_keywords = extract_ats_keywords
        self.format_ats_contact_block = format_ats_contact_block
        self.audit_ats_cv_compatibility = audit_ats_cv_compatibility

        self.mock_job = {
            "title": "Senior AI Platform Engineer",
            "company": "DeepTech Labs",
            "description": "We are seeking a Senior AI Platform Engineer experienced in Python, Kubernetes, Docker, and LLM agent orchestration. Must have strong distributed systems and CI/CD background.",
            "tags": ["Python", "Kubernetes", "Docker", "LLM", "GCP"],
            "matched_skills": ["Python", "Kubernetes", "Docker"],
        }
        self.mock_profile = {
            "full_name": "Sarah Connor",
            "email": "sarah.connor@example.com",
            "phone": "+1 (555) 432-1098",
            "location": "San Francisco, CA",
            "linkedin_url": "linkedin.com/in/sarahconnor",
            "core_skills": ["Python", "Kubernetes", "Docker", "GCP", "PyTorch"],
        }

    def test_extract_ats_keywords(self):
        result = self.extract_ats_keywords(self.mock_job, self.mock_profile)
        self.assertIn("priority_keywords", result)
        self.assertIn("title_keywords", result)
        self.assertIn("hard_skills", result)
        self.assertGreater(len(result["priority_keywords"]), 0)
        # Check that high-value tech keywords were detected
        hard_kw_lower = [k.lower() for k in result["hard_skills"]]
        self.assertTrue(any(k in hard_kw_lower for k in ["python", "kubernetes", "docker"]))

    def test_format_ats_contact_block(self):
        block = self.format_ats_contact_block(self.mock_profile)
        self.assertIn("SARAH CONNOR", block.upper())
        self.assertIn("sarah.connor@example.com", block)
        self.assertIn("San Francisco, CA", block)

    def test_audit_ats_cv_compatibility(self):
        sample_cv = """# Sarah Connor
sarah.connor@example.com | (555) 432-1098 | San Francisco, CA

## PROFESSIONAL SUMMARY
Senior AI Platform Engineer with 8+ years scaling Python, Docker, Kubernetes, and LLM pipelines.

## CORE COMPETENCIES
- Python, Docker, Kubernetes, GCP, PyTorch, CI/CD, Distributed Systems

## PROFESSIONAL EXPERIENCE
### Staff AI Engineer | TechCorp
- Scaled inference latency by 45% using Kubernetes and Docker.
- Spearheaded LLM multi-agent pipelines for 1.2M monthly users.
"""
        audit = self.audit_ats_cv_compatibility(sample_cv, self.mock_job, self.mock_profile)
        self.assertIn("ats_score", audit)
        self.assertIn("grade", audit)
        self.assertIn("matched_keywords", audit)
        self.assertIn("compliance_checks", audit)
        self.assertGreaterEqual(audit["ats_score"], 60)
        self.assertEqual(len(audit["compliance_checks"]), 5)


class TestDocumentExporter(unittest.TestCase):
    """Verifies standard ATS PDF and DOCX generation for resumes and cover letters."""

    def setUp(self):
        from src.utils.document_exporter import (
            sanitize_text_for_pdf,
            create_cv_pdf,
            create_cv_docx,
            create_cover_letter_pdf,
            create_cover_letter_docx,
        )
        self.sanitize_text_for_pdf = sanitize_text_for_pdf
        self.create_cv_pdf = create_cv_pdf
        self.create_cv_docx = create_cv_docx
        self.create_cover_letter_pdf = create_cover_letter_pdf
        self.create_cover_letter_docx = create_cover_letter_docx

        self.cv_md = """# Sarah Connor
sarah.connor@example.com | San Francisco, CA

## PROFESSIONAL SUMMARY
Senior Platform Architect experienced with distributed systems.

## EXPERIENCE
### Staff Engineer | Apex Systems
- Built resilient high-concurrency systems.
"""
        self.cl_text = """Dear Hiring Team,

I am writing to express my strong interest in the Senior AI Platform Engineer role.

Best regards,
Sarah Connor"""

    def test_sanitize_text(self):
        dirty = "Check this — and this – bullet • and check ✔ ⚡"
        clean = self.sanitize_text_for_pdf(dirty)
        self.assertNotIn("—", clean)
        self.assertNotIn("–", clean)
        self.assertNotIn("✔", clean)

    def test_create_cv_pdf(self):
        pdf_buf = self.create_cv_pdf(self.cv_md, candidate_name="Sarah Connor")
        self.assertIsInstance(pdf_buf, io.BytesIO)
        self.assertGreater(len(pdf_buf.getvalue()), 500)

    def test_create_cv_docx(self):
        docx_buf = self.create_cv_docx(self.cv_md)
        self.assertIsInstance(docx_buf, io.BytesIO)
        self.assertGreater(len(docx_buf.getvalue()), 500)

    def test_create_cover_letter_pdf(self):
        cl_pdf = self.create_cover_letter_pdf(self.cl_text, candidate_name="Sarah Connor", company="DeepTech Labs")
        self.assertIsInstance(cl_pdf, io.BytesIO)
        self.assertGreater(len(cl_pdf.getvalue()), 500)

    def test_create_cover_letter_docx(self):
        cl_docx = self.create_cover_letter_docx(self.cl_text, candidate_name="Sarah Connor", company="DeepTech Labs")
        self.assertIsInstance(cl_docx, io.BytesIO)
        self.assertGreater(len(cl_docx.getvalue()), 500)


class TestPipelineManager(unittest.TestCase):
    """Verifies application Kanban tracking and state updates."""

    def setUp(self):
        import streamlit as st
        from src.utils.pipeline_manager import (
            STAGE_SAVED,
            STAGE_APPLIED,
            STAGE_INTERVIEWING,
            get_pipeline,
            add_or_update_pipeline,
            set_job_stage,
            remove_from_pipeline,
            update_job_notes,
        )
        self.st = st
        self.st.session_state["application_pipeline"] = {}
        self.STAGE_SAVED = STAGE_SAVED
        self.STAGE_APPLIED = STAGE_APPLIED
        self.STAGE_INTERVIEWING = STAGE_INTERVIEWING
        self.get_pipeline = get_pipeline
        self.add_or_update_pipeline = add_or_update_pipeline
        self.set_job_stage = set_job_stage
        self.remove_from_pipeline = remove_from_pipeline
        self.update_job_notes = update_job_notes

    def test_pipeline_lifecycle(self):
        job = {
            "id": "job_101",
            "title": "Lead ML Engineer",
            "company": "Anthropic",
            "location": "San Francisco, CA",
            "fit_score": 96,
        }
        # 1. Add to pipeline
        self.add_or_update_pipeline(job, initial_stage=self.STAGE_SAVED)
        pipeline = self.get_pipeline()
        self.assertIn("job_101", pipeline)
        self.assertEqual(pipeline["job_101"]["stage"], self.STAGE_SAVED)
        self.assertEqual(pipeline["job_101"]["company"], "Anthropic")

        # 2. Transition stage
        self.set_job_stage("job_101", self.STAGE_APPLIED)
        self.assertEqual(self.get_pipeline()["job_101"]["stage"], self.STAGE_APPLIED)

        # 3. Update notes
        self.update_job_notes("job_101", "Completed screening call.")
        self.assertEqual(self.get_pipeline()["job_101"]["notes"], "Completed screening call.")

        # 4. Remove from pipeline
        self.remove_from_pipeline("job_101")
        self.assertNotIn("job_101", self.get_pipeline())


class TestSalaryEvaluator(unittest.TestCase):
    """Verifies compensation benchmarks and salary offer evaluation."""

    def setUp(self):
        from src.utils.salary_evaluator import (
            parse_numeric_salary,
            parse_salary_range,
            detect_role_domain,
            detect_seniority_tier,
            evaluate_job_salary,
        )
        self.parse_numeric_salary = parse_numeric_salary
        self.parse_salary_range = parse_salary_range
        self.detect_role_domain = detect_role_domain
        self.detect_seniority_tier = detect_seniority_tier
        self.evaluate_job_salary = evaluate_job_salary

    def test_parse_numeric_salary(self):
        val = self.parse_numeric_salary("$185,000 / yr")
        self.assertEqual(val, 185000.0)

    def test_parse_salary_range(self):
        raw = "$180,000 - $220,000 a year"
        parsed = self.parse_salary_range(raw)
        self.assertTrue(parsed["has_salary"])
        self.assertEqual(parsed["currency_symbol"], "$")
        self.assertEqual(parsed["min_usd"], 180000.0)
        self.assertEqual(parsed["max_usd"], 220000.0)

    def test_detect_role_domain(self):
        domain = self.detect_role_domain("Staff Machine Learning Engineer")
        self.assertEqual(domain, "ai_ml")

        pm_domain = self.detect_role_domain("Principal Product Manager")
        self.assertEqual(pm_domain, "product")

    def test_detect_seniority_tier(self):
        tier = self.detect_seniority_tier("Staff Software Engineer")
        self.assertEqual(tier, "lead_staff")

        mid_tier = self.detect_seniority_tier("Software Engineer", "3-5 years")
        self.assertEqual(mid_tier, "mid")

    def test_evaluate_job_salary(self):
        job_title = "Senior AI Engineer"
        salary_str = "$210,000 - $260,000 / yr"
        profile = {
            "target_role": "Senior AI Engineer",
            "location": "San Francisco, CA",
            "work_mode": "Hybrid",
            "preferred_min_salary": "$180,000",
        }
        eval_result = self.evaluate_job_salary(salary_str, job_title=job_title, profile=profile)
        self.assertIn("score", eval_result)
        self.assertIn("rank", eval_result)
        self.assertIn("assessment", eval_result)
        self.assertIn(eval_result["rank"], ["Competitive", "Top of Market", "Fair Market", "Below Market", "Above Market"])


class TestUserManager(unittest.TestCase):
    """Verifies multi-user isolation, registry persistence, and workspaces."""

    def setUp(self):
        from src.utils.user_manager import (
            get_registry,
            get_all_users,
            get_user_profile,
            save_user_profile,
            get_user_workspace,
        )
        self.get_registry = get_registry
        self.get_all_users = get_all_users
        self.get_user_profile = get_user_profile
        self.save_user_profile = save_user_profile
        self.get_user_workspace = get_user_workspace

    def test_user_registry_and_profile_flow(self):
        users = self.get_all_users()
        self.assertIsInstance(users, list)
        self.assertGreaterEqual(len(users), 1)

        default_user_id = users[0]["id"]
        profile = self.get_user_profile(default_user_id)
        self.assertIsNotNone(profile)
        self.assertIn("full_name", profile)
        self.assertIn("target_role", profile)

        workspace = self.get_user_workspace(default_user_id)
        self.assertIsInstance(workspace, dict)


class TestJobScraperUtils(unittest.TestCase):
    """Verifies job parsing, regex country matching, work mode classification, and semantic scoring."""

    def setUp(self):
        from src.agents.job_scraper_agent import (
            clean_html_text,
            normalize_company_slug,
            extract_target_countries,
            check_job_country_match,
            determine_work_mode,
            calculate_semantic_fit,
        )
        self.clean_html_text = clean_html_text
        self.normalize_company_slug = normalize_company_slug
        self.extract_target_countries = extract_target_countries
        self.check_job_country_match = check_job_country_match
        self.determine_work_mode = determine_work_mode
        self.calculate_semantic_fit = calculate_semantic_fit

    def test_clean_html_text(self):
        raw = "<p>We are hiring <strong>AI Engineers</strong> &amp; Leaders!</p>"
        clean = self.clean_html_text(raw)
        self.assertEqual(clean, "We are hiring AI Engineers & Leaders!")

    def test_normalize_company_slug(self):
        self.assertEqual(self.normalize_company_slug("Perplexity AI"), "perplexityai")
        self.assertEqual(self.normalize_company_slug("Bain & Company"), "bainandcompany")

    def test_extract_target_countries(self):
        countries = self.extract_target_countries("London, United Kingdom; Berlin, Germany")
        self.assertIn("united kingdom", countries)
        self.assertIn("germany", countries)

    def test_check_job_country_match(self):
        is_match, matched = self.check_job_country_match("Munich, DE", ["germany"])
        self.assertTrue(is_match)
        self.assertEqual(matched, "Germany")

        is_match_uk, _ = self.check_job_country_match("Paris, France", ["united kingdom"])
        self.assertFalse(is_match_uk)

    def test_determine_work_mode(self):
        remote_job = {"title": "Software Engineer", "location": "Remote - Worldwide"}
        mode, is_rem, is_hyb, is_ons = self.determine_work_mode(remote_job)
        self.assertTrue(is_rem)
        self.assertFalse(is_ons)

        hybrid_job = {"title": "Product Designer", "location": "London, UK (Hybrid)"}
        mode_h, is_rem_h, is_hyb_h, is_ons_h = self.determine_work_mode(hybrid_job)
        self.assertTrue(is_hyb_h)

    def test_calculate_semantic_fit(self):
        job = {
            "title": "Principal AI Architect",
            "company": "Cortex AI",
            "location": "Remote",
            "description": "Designing agentic LLM platforms with Python, FastAPI, Kubernetes, and Vector Databases.",
            "tags": ["Python", "FastAPI", "Kubernetes"],
        }
        profile = {
            "target_role": "Principal AI Architect",
            "core_skills": ["Python", "FastAPI", "Kubernetes", "LLM", "Docker"],
            "experience_highlights": ["Architected AI agent systems"],
            "years_of_experience": "10+",
        }
        score, matched_skills, reasons, mode = self.calculate_semantic_fit(job, profile, [])
        self.assertGreaterEqual(score, 80)
        self.assertIn("Python", matched_skills)
        self.assertGreater(len(reasons), 0)

    def test_evaluate_role_match(self):
        from src.agents.matching.scoring import evaluate_role_match
        profile = {
            "headline": "Senior AI / Agentic Systems Engineer",
            "core_skills": ["Google Antigravity SDK", "Gemini API", "Python", "RAG"],
            "years_of_experience": "6+ years",
        }
        res1 = evaluate_role_match("Senior AI / Agentic Systems Engineer", profile)
        self.assertGreaterEqual(res1["score"], 90)
        self.assertEqual(res1["match_label"], "Exceptional Fit")
        self.assertIn("rationale", res1)
        self.assertIn("seniority_assessment", res1)
        self.assertGreater(len(res1["strengths"]), 0)
        self.assertGreater(len(res1["recommendations"]), 0)

        res2 = evaluate_role_match("Junior Marketing Intern", profile)
        self.assertLess(res2["score"], 85)

        # Verify screen 2 dialog function export
        from src.views.screen2_review import show_recruiter_analysis_dialog
        self.assertTrue(callable(show_recruiter_analysis_dialog))


class TestCompanyIntelligenceAgent(unittest.TestCase):

    """Verifies executive company dossier generation and fallback."""

    def setUp(self):
        from src.agents.company_intelligence_agent import (
            get_mock_company_dossier,
            generate_company_dossier,
        )
        self.get_mock_company_dossier = get_mock_company_dossier
        self.generate_company_dossier = generate_company_dossier

    def test_company_dossier_structure(self):
        dossier = self.generate_company_dossier("Vercel", job_title="Staff Frontend Architect")
        self.assertEqual(dossier["company_name"], "Vercel")
        self.assertIn("stage_and_funding", dossier)
        self.assertIn("tech_stack", dossier)
        self.assertIn("leadership_team", dossier)
        self.assertIn("strategic_interview_questions", dossier)
        self.assertGreaterEqual(len(dossier["strategic_interview_questions"]), 3)


class TestJobScoutAgent(unittest.TestCase):
    """Verifies autonomous job scout cycle and morning career digest structure."""

    def setUp(self):
        from src.agents.job_scout_agent import run_job_scout_cycle
        self.run_job_scout_cycle = run_job_scout_cycle

    def test_job_scout_cycle(self):
        profile = {
            "full_name": "Jordan Lee",
            "headline": "Full Stack Lead Engineer",
            "target_role": "Full Stack Lead Engineer",
            "location": "Remote",
            "work_mode": "Remote Only",
            "core_skills": ["TypeScript", "React", "Node.js", "Python"],
        }
        result = self.run_job_scout_cycle(profile, existing_job_ids=set())
        self.assertIn("digest", result)
        digest = result["digest"]
        self.assertIn("headline", digest)
        self.assertIn("market_signals", digest)
        self.assertIn("featured_jobs", digest)
        self.assertIn("stats", digest)
        self.assertGreaterEqual(len(digest["featured_jobs"]), 1)


class TestApplicationAgent(unittest.TestCase):
    """Verifies tailored CV and cover letter synthesis."""

    def setUp(self):
        from src.agents.application_agent import (
            generate_customized_cv,
            generate_customized_cover_letter,
        )
        self.generate_customized_cv = generate_customized_cv
        self.generate_customized_cover_letter = generate_customized_cover_letter

        self.mock_job = {
            "id": "job_99",
            "title": "Senior Solutions Architect",
            "company": "CloudWave",
            "description": "Looking for a Senior Solutions Architect with deep experience in cloud migration, Python, and system design.",
            "matched_skills": ["Cloud Migration", "Python", "System Design"],
            "key_reasons": ["Extensive system design expertise"],
        }
        self.mock_profile = {
            "full_name": "Marcus Aurelius",
            "headline": "Senior Solutions Architect",
            "email": "marcus@cloudwave.example",
            "core_skills": ["Python", "Cloud Migration", "Kubernetes", "AWS"],
            "experience_highlights": ["Led multi-region AWS cloud migration"],
        }

    def test_generate_customized_cv(self):
        cv = self.generate_customized_cv(self.mock_job, self.mock_profile)
        self.assertIn("MARCUS AURELIUS", cv.upper())
        self.assertIn("CloudWave", cv)
        self.assertIn("PROFESSIONAL EXPERIENCE", cv.upper())

    def test_generate_customized_cover_letter(self):
        cl = self.generate_customized_cover_letter(self.mock_job, self.mock_profile)
        self.assertIn("CloudWave", cl)
        self.assertIn("Marcus Aurelius", cl)


class TestInterviewPrepAgent(unittest.TestCase):
    """Verifies interview preparation pack generation."""

    def setUp(self):
        from src.agents.interview_prep_agent import generate_interview_prep_pack
        self.generate_interview_prep_pack = generate_interview_prep_pack

        self.mock_job = {
            "title": "Director of Engineering",
            "company": "Stripe",
            "description": "Leading global payment infrastructure teams.",
            "matched_skills": ["Distributed Systems", "Payments", "Team Leadership"],
        }
        self.mock_profile = {
            "full_name": "Devon Vance",
            "years_of_experience": "12+",
            "core_skills": ["Distributed Systems", "Team Leadership"],
        }

    def test_generate_interview_prep_pack(self):
        pack = self.generate_interview_prep_pack(self.mock_job, self.mock_profile)
        self.assertIn("raw_markdown", pack)
        self.assertIn("candidate_name", pack)
        self.assertIn("briefing", pack)
        self.assertIn("technical_qa", pack)
        self.assertIn("Stripe", pack["raw_markdown"])
        self.assertIn("Executive Interview Briefing", pack["raw_markdown"])


class TestOutreachAgent(unittest.TestCase):
    """Verifies multi-channel recruiter outreach message drafting."""

    def setUp(self):
        from src.agents.outreach_agent import generate_outreach_campaign
        self.generate_outreach_campaign = generate_outreach_campaign

        self.mock_job = {
            "title": "Principal AI Researcher",
            "company": "Mistral AI",
            "description": "Frontier model training and evaluation.",
            "matched_skills": ["PyTorch", "LLMs", "Transformers"],
        }
        self.mock_profile = {
            "full_name": "Elena Rostova",
            "core_skills": ["PyTorch", "Transformers", "LLMs"],
        }

    def test_generate_outreach_campaign(self):
        campaign = self.generate_outreach_campaign(self.mock_job, self.mock_profile)
        self.assertIn("linkedin_note", campaign)
        self.assertIn("hiring_manager_email", campaign)
        self.assertIn("recruiter_inmail", campaign)
        self.assertIn("referral_request", campaign)
        self.assertIn("thank_you_note", campaign)
        # Verify strict LinkedIn character budget rule (<= 300 chars)
        note_text = campaign["linkedin_note"]["text"]
        self.assertLessEqual(len(note_text), 300)


class TestResumeParserAgent(unittest.TestCase):
    """Verifies skill extraction and resume heuristic parsing."""

    def setUp(self):
        from src.agents.resume_parser_agent import (
            extract_skills_from_text,
            extract_candidate_name_from_text,
            detect_experience_level,
            extract_initial_profile_from_text,
        )
        self.extract_skills_from_text = extract_skills_from_text
        self.extract_candidate_name_from_text = extract_candidate_name_from_text
        self.detect_experience_level = detect_experience_level
        self.extract_initial_profile_from_text = extract_initial_profile_from_text

        self.sample_resume = """Alex Vance
alex.vance@blackmesa.org | (555) 019-2834 | City 17

PROFESSIONAL SUMMARY
Senior Robotics & AI Engineer with 9 years of experience designing autonomous systems in Python, C++, ROS, and PyTorch.

SKILLS
Python, C++, Docker, Kubernetes, PyTorch, ROS, Git, Linux
"""

    def test_extract_skills(self):
        skills = self.extract_skills_from_text(self.sample_resume)
        self.assertIn("Python", skills)
        self.assertIn("Docker", skills)

    def test_extract_candidate_name(self):
        name = self.extract_candidate_name_from_text(self.sample_resume)
        self.assertEqual(name, "Alex Vance")

    def test_detect_experience_level(self):
        exp = self.detect_experience_level(self.sample_resume)
        self.assertIn("years", exp.lower())

    def test_extract_initial_profile(self):
        profile = self.extract_initial_profile_from_text(self.sample_resume)
        self.assertEqual(profile["full_name"], "Alex Vance")
        self.assertIn("Python", profile["core_skills"])


class TestStateManagement(unittest.TestCase):
    """Verifies Streamlit session state initialization and navigation."""

    def setUp(self):
        import streamlit as st
        from src.state import (
            init_session_state,
            go_to_screen,
            reset_wizard,
            SCREEN_REGISTRY,
            SCREEN_INPUT,
            SCREEN_DASHBOARD,
        )
        self.st = st
        self.init_session_state = init_session_state
        self.go_to_screen = go_to_screen
        self.reset_wizard = reset_wizard
        self.SCREEN_REGISTRY = SCREEN_REGISTRY
        self.SCREEN_INPUT = SCREEN_INPUT
        self.SCREEN_DASHBOARD = SCREEN_DASHBOARD

    def test_state_flow(self):
        self.init_session_state()
        self.assertIn("current_screen", self.st.session_state)

        self.go_to_screen(self.SCREEN_INPUT)
        self.assertEqual(self.st.session_state.current_screen, self.SCREEN_INPUT)

        self.go_to_screen(self.SCREEN_DASHBOARD)
        self.assertEqual(self.st.session_state.current_screen, self.SCREEN_DASHBOARD)


if __name__ == "__main__":
    unittest.main(verbosity=2)
