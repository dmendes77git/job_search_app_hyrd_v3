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
            detect_job_language,
        )
        self.extract_ats_keywords = extract_ats_keywords
        self.format_ats_contact_block = format_ats_contact_block
        self.audit_ats_cv_compatibility = audit_ats_cv_compatibility
        self.detect_job_language = detect_job_language

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
        self.assertIn("Target Role:", block)

    def test_format_ats_contact_block_portuguese(self):
        block = self.format_ats_contact_block(self.mock_profile, target_role="Engenheiro de Software", company="TechPT", language="pt-pt")
        self.assertIn("SARAH CONNOR", block.upper())
        self.assertIn("sarah.connor@example.com", block)
        self.assertIn("Cargo Pretendido:", block)
        self.assertIn("**Empresa Alvo:** TechPT", block)

    def test_detect_job_language(self):
        pt_job = {
            "title": "Engenheiro de Software Sénior",
            "company": "Empresa Tecnológica",
            "source": "ITJobs.pt",
            "location": "Lisboa, Portugal",
            "description": "Procuramos um profissional com sólida experiência em desenvolvimento de software e microsserviços. Requisitos essenciais e integração em equipa dinâmica.",
            "tags": ["lisboa", "desenvolvimento", "remoto"],
        }
        self.assertEqual(self.detect_job_language(pt_job), "pt-pt")

        net_job = {
            "title": "Programador Python",
            "company": "Startup",
            "source": "Net-Empregos",
            "location": "Porto, Portugal",
            "description": "Excelente oportunidade de emprego. Oferecemos vencimento compatível com a experiência e trabalho híbrido.",
            "tags": ["emprego", "porto"],
        }
        self.assertEqual(self.detect_job_language(net_job), "pt-pt")

        en_job = {
            "title": "Senior AI Systems Engineer",
            "company": "Tech Labs",
            "source": "Greenhouse",
            "location": "Remote",
            "description": "Looking for an experienced engineer with deep knowledge of Kubernetes, Python, and distributed systems.",
            "tags": ["remote", "python"],
        }
        self.assertEqual(self.detect_job_language(en_job), "en")

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

    def test_audit_ats_cv_compatibility_portuguese(self):
        sample_pt_cv = """# Sarah Connor
**Cargo Pretendido:** Engenheiro de Software | **Empresa Alvo:** TechPT
sarah.connor@example.com • +351 912 345 678 • Lisboa, Portugal • linkedin.com/in/sarahconnor

---

## RESUMO PROFISSIONAL
Engenheiro de Software Sénior com mais de 8 anos de experiência comprovada no desenvolvimento de microsserviços em Python, Docker e Kubernetes, alcançando melhorias de desempenho de 45% e liderando projetos críticos com 99,9% de disponibilidade.

---

## COMPETÊNCIAS TÉCNICAS & HABILIDADES
- **Linguagens e Frameworks:** Python, Docker, Kubernetes, FastAPI, PostgreSQL, CI/CD, microsserviços, inteligência artificial

---

## EXPERIÊNCIA PROFISSIONAL
### Engenheiro de Software Sénior | Empresa Tecnológica
*Janeiro de 2021 - Presente | Lisboa, Portugal (Remoto)*
- Otimizou o débito operacional dos serviços em 60% através da implementação de arquiteturas orientadas a eventos.
- Liderou uma equipa técnica distribuída de 5 engenheiros, reduzindo o tempo de entrega de novas funcionalidades em 3.5x.

---

## FORMAÇÃO ACADÉMICA & CERTIFICAÇÕES
- **Licenciatura em Engenharia Informática** — Universidade de Lisboa
- **Certificação Google Cloud Professional Data Engineer**
"""
        pt_job = {
            "title": "Engenheiro de Software",
            "company": "TechPT",
            "description": "Procuramos Engenheiro de Software com experiência em Python, Docker, Kubernetes e microsserviços.",
            "tags": ["Python", "Docker", "Kubernetes", "Microsserviços"],
            "matched_skills": ["Python", "Docker", "Kubernetes"],
        }
        audit = self.audit_ats_cv_compatibility(sample_pt_cv, pt_job, self.mock_profile)
        self.assertIn("ats_score", audit)
        self.assertGreaterEqual(audit["ats_score"], 85)
        # Verify all 4 standard headings were recognized under Portuguese naming
        heading_check = next((c for c in audit["compliance_checks"] if "Section Headings" in c["name"]), None)
        self.assertIsNotNone(heading_check)
        self.assertTrue(heading_check["status"])


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

        # Test Target Location & Countries calibration (Germany)
        de_profile = {
            "target_role": "Senior AI Engineer",
            "target_location": "Berlin, Germany",
            "preferred_min_salary": "€100,000",
        }
        de_eval = self.evaluate_job_salary(
            "€115,000 - €135,000",
            job_title="Senior AI Engineer",
            profile=de_profile,
            target_location="Berlin, Germany",
        )
        self.assertEqual(de_eval["location_name"], "Germany")
        self.assertEqual(de_eval["location_factor"], 0.78)
        self.assertIn(de_eval["rank"], ["Within Market Standard", "Above Market"])
        self.assertGreaterEqual(de_eval["score"], 75)
        self.assertIn("Germany", de_eval["location_badge"])

        # Test UK calibration
        uk_eval = self.evaluate_job_salary(
            "£95,000 - £120,000",
            job_title="Senior AI Engineer",
            target_location="London, United Kingdom",
        )
        self.assertEqual(uk_eval["location_name"], "United Kingdom")
        self.assertEqual(uk_eval["location_factor"], 0.82)
        self.assertIn(uk_eval["rank"], ["Within Market Standard", "Above Market"])


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
        self.assertIn("gap_to_100", res1)
        gap1 = res1["gap_to_100"]
        self.assertGreater(len(gap1["missing_skills"]), 0)
        self.assertGreater(len(gap1["experience_gaps"]), 0)
        self.assertGreater(len(gap1["certifications"]), 0)
        self.assertIn("summary", gap1)

        res2 = evaluate_role_match("Junior Marketing Intern", profile)
        self.assertLess(res2["score"], 85)
        self.assertIn("gap_to_100", res2)

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


class TestDateFreshnessUtils(unittest.TestCase):
    """Verifies parsing of job posting freshness and calculation of days since posted."""

    def setUp(self):
        from src.utils.date_utils import parse_days_since_posted
        self.parse_days_since_posted = parse_days_since_posted

    def test_relative_days(self):
        days, label = self.parse_days_since_posted("1 day ago")
        self.assertEqual(days, 1)
        self.assertEqual(label, "1 day ago")

        days3, label3 = self.parse_days_since_posted("3 days ago")
        self.assertEqual(days3, 3)
        self.assertEqual(label3, "3 days ago")

    def test_relative_weeks_and_months(self):
        days_w, label_w = self.parse_days_since_posted("2 weeks ago")
        self.assertEqual(days_w, 14)
        self.assertIn("14 days ago", label_w)

        days_m, label_m = self.parse_days_since_posted("1 month ago")
        self.assertEqual(days_m, 30)
        self.assertIn("30 days ago", label_m)

    def test_today_and_feed_keywords(self):
        days_now, label_now = self.parse_days_since_posted("Just now")
        self.assertEqual(days_now, 0)
        self.assertIn("Posted today", label_now)

        days_zip, label_zip = self.parse_days_since_posted("Active on ZipRecruiter", job_id="test-123")
        self.assertIn(days_zip, [1, 2])
        self.assertIn("Active", label_zip)

    def test_iso_dates(self):
        from datetime import date, timedelta
        today_iso = date.today().isoformat()
        days_today, label_today = self.parse_days_since_posted(today_iso)
        self.assertEqual(days_today, 0)

        four_days_ago_iso = (date.today() - timedelta(days=4)).isoformat()
        days_4, label_4 = self.parse_days_since_posted(four_days_ago_iso)
        self.assertEqual(days_4, 4)
        self.assertEqual(label_4, "4 days ago")

    def test_european_dates(self):
        from datetime import date, timedelta
        today_eu = date.today().strftime("%d-%m-%Y")
        days_today, label_today = self.parse_days_since_posted(today_eu)
        self.assertEqual(days_today, 0)

        three_days_ago_eu = (date.today() - timedelta(days=3)).strftime("%d-%m-%Y")
        days_3, label_3 = self.parse_days_since_posted(three_days_ago_eu)
        self.assertEqual(days_3, 3)
        self.assertEqual(label_3, "3 days ago")


class TestPortugueseScrapers(unittest.TestCase):
    """Verifies Portuguese job board scrapers (ITJobs.pt, Net-Empregos, Landing.jobs) and regional matching."""

    def test_itjobs_scraper(self):
        from src.agents.scrapers.portuguese_scrapers import fetch_itjobs_jobs
        jobs = fetch_itjobs_jobs(target_query="python", limit=2)
        self.assertIsInstance(jobs, list)
        if jobs:
            j = jobs[0]
            self.assertIn("id", j)
            self.assertIn("title", j)
            self.assertEqual(j["source"], "ITJobs.pt")
            self.assertTrue(j["url"].startswith("http"))

    def test_netempregos_scraper(self):
        from src.agents.scrapers.portuguese_scrapers import fetch_netempregos_jobs
        jobs = fetch_netempregos_jobs(target_query="python", limit=2)
        self.assertIsInstance(jobs, list)
        if jobs:
            j = jobs[0]
            self.assertIn("id", j)
            self.assertIn("title", j)
            self.assertEqual(j["source"], "Net-Empregos")
            self.assertTrue(j["url"].startswith("http"))

    def test_landingjobs_scraper(self):
        from src.agents.scrapers.portuguese_scrapers import fetch_landingjobs_jobs
        jobs = fetch_landingjobs_jobs(target_query="python", limit=2)
        self.assertIsInstance(jobs, list)
        if jobs:
            j = jobs[0]
            self.assertIn("id", j)
            self.assertIn("title", j)
            self.assertEqual(j["source"], "Landing.jobs")
            self.assertTrue(j["url"].startswith("http"))

    def test_portuguese_location_and_work_mode(self):
        from src.agents.matching.scoring import extract_target_countries, determine_work_mode
        # Test Portuguese city synonyms map to portugal
        for city in ["lisboa", "porto", "braga", "coimbra", "funchal", "oeiras"]:
            countries = extract_target_countries(f"{city}, Portugal")
            self.assertIn("portugal", countries)

        # Test Portuguese work mode tokens
        remote_job = {"location": "Lisboa", "description": "Trabalho 100% remoto para engenharia"}
        label, is_rem, is_hyb, is_onsite = determine_work_mode(remote_job)
        self.assertTrue(is_rem)

        hybrid_job = {"location": "Porto", "description": "Modelo híbrido 2 dias no escritório"}
        label_h, is_rem_h, is_hyb_h, is_onsite_h = determine_work_mode(hybrid_job)
        self.assertTrue(is_hyb_h)


class TestMatchingAndSearchEnhancements(unittest.TestCase):
    """Verifies Points 1, 2, and 3: Search Query Optimization, Multi-Dimensional Scoring, and Tech Stack Matrix."""

    def test_role_synonyms_and_query_optimization(self):
        from src.agents.matching.scoring import expand_role_synonyms
        from src.agents.job_scraper_agent import optimize_query_for_source

        # Test Synonym Expansion (Point 1.C)
        syns = expand_role_synonyms("Senior AI Engineer")
        self.assertIn("Machine Learning Engineer", syns)
        self.assertIn("Llm Engineer", syns)

        # Test Query Optimization for ATS vs Boolean boards (Point 1.B)
        ats_q = optimize_query_for_source("Senior Staff Generative AI Software Engineer (Remote Only)", "Ashby")
        self.assertEqual(ats_q, "AI Engineer")

        clean_q = optimize_query_for_source("Senior Python Engineer (US Remote)", "LinkedIn")
        self.assertEqual(clean_q, "Senior Python Engineer")

    def test_freshness_decay_boost(self):
        from src.agents.matching.scoring import calculate_semantic_fit

        profile = {
            "target_role": "Python Developer",
            "core_skills": ["Python", "FastAPI", "Docker"],
            "work_mode": "Remote Only",
        }
        # Hot job (0 days / today)
        job_hot = {
            "title": "Python Developer",
            "company": "FastTech",
            "location": "Remote",
            "description": "Python, FastAPI development",
            "posted": "today",
        }
        # Stale job (>21 days)
        job_stale = {
            "title": "Python Developer",
            "company": "SlowCorp",
            "location": "Remote",
            "description": "Python, FastAPI development",
            "posted": "30 days ago",
        }
        score_hot, _, reasons_hot, _ = calculate_semantic_fit(job_hot, profile, [])
        score_stale, _, reasons_stale, _ = calculate_semantic_fit(job_stale, profile, [])

        self.assertGreater(score_hot, score_stale)
        self.assertTrue(any("Fresh requisition" in r or "Hot" in r for r in reasons_hot))
        self.assertTrue(any("Aging" in r for r in reasons_stale))

    def test_core_anchor_vs_secondary_skill_weighting(self):
        from src.agents.matching.scoring import calculate_semantic_fit

        profile = {
            "target_role": "AI Engineer",
            "core_skills": ["PyTorch", "Python", "LLM", "Docker", "Git", "Jira"],
            "work_mode": "Remote Only",
        }
        # Job matching primary core anchors (PyTorch, Python, LLM)
        job_anchor = {
            "title": "AI Engineer",
            "location": "Remote",
            "description": "Building agentic systems with PyTorch and Python and LLM",
        }
        # Job matching only secondary administrative tools (Git, Jira)
        job_secondary = {
            "title": "AI Engineer",
            "location": "Remote",
            "description": "Project management tracking with Git and Jira",
        }
        score_anchor, matched_anchor, _, _ = calculate_semantic_fit(job_anchor, profile, [])
        score_sec, matched_sec, _, _ = calculate_semantic_fit(job_secondary, profile, [])

        self.assertGreater(score_anchor, score_sec)
        self.assertIn("PyTorch", matched_anchor)

    def test_years_experience_leveling_calibration(self):
        from src.agents.matching.scoring import calculate_semantic_fit, extract_required_years_experience

        self.assertEqual(extract_required_years_experience("Requires minimum 5+ years of relevant experience"), 5)
        self.assertEqual(extract_required_years_experience("3-5 yrs experience in software"), 3)

        senior_profile = {
            "target_role": "Software Engineer",
            "years_of_experience": "8+ years",
            "core_skills": ["Java", "Spring Boot"],
        }
        job_matching_level = {
            "title": "Software Engineer",
            "location": "Remote",
            "description": "Requires 5+ years of hands-on Java development with Spring Boot",
        }
        job_too_junior = {
            "title": "Software Engineer",
            "location": "Remote",
            "description": "Entry level role requiring 1 year of experience in Java",
        }
        score_level, _, reasons_level, _ = calculate_semantic_fit(job_matching_level, senior_profile, [])
        score_jun, _, reasons_jun, _ = calculate_semantic_fit(job_too_junior, senior_profile, [])

        self.assertGreater(score_level, score_jun)
        self.assertTrue(any("Leveling match" in r for r in reasons_level))

    def test_salary_fit_factor(self):
        from src.agents.matching.scoring import calculate_semantic_fit

        profile_high_sal = {
            "target_role": "Backend Engineer",
            "preferred_min_salary": "$150,000",
            "core_skills": ["Go", "Kubernetes"],
        }
        job_good_sal = {
            "title": "Backend Engineer",
            "location": "Remote",
            "salary": "$160,000 - $185,000",
            "description": "Go microservices in Kubernetes",
        }
        job_low_sal = {
            "title": "Backend Engineer",
            "location": "Remote",
            "salary": "$60,000 - $75,000",
            "description": "Go microservices in Kubernetes",
        }
        score_good, _, reasons_good, _ = calculate_semantic_fit(job_good_sal, profile_high_sal, [])
        score_low, _, reasons_low, _ = calculate_semantic_fit(job_low_sal, profile_high_sal, [])

        self.assertGreater(score_good, score_low)
        self.assertTrue(any("Compensation alignment" in r for r in reasons_good))
        self.assertTrue(any("Compensation advisory" in r for r in reasons_low))

    def test_tech_stack_extraction_and_missing_skills(self):
        from src.agents.matching.scoring import calculate_semantic_fit, extract_tech_skills

        skills = extract_tech_skills("We build with Python, PyTorch, Docker, Kubernetes, Kafka, and Redis.")
        self.assertIn("Python", skills)
        self.assertIn("Docker", skills)
        self.assertIn("Kafka", skills)

        profile = {
            "target_role": "ML Engineer",
            "core_skills": ["Python", "PyTorch"],
        }
        job = {
            "title": "ML Engineer",
            "location": "Remote",
            "description": "Build ML microservices with Python, PyTorch, Kubernetes, and Kafka.",
        }
        calculate_semantic_fit(job, profile, [])

        self.assertIn("missing_skills", job)
        self.assertIn("Kubernetes", job["missing_skills"])
        self.assertIn("Kafka", job["missing_skills"])


class TestPortugueseApplicationAndScraping(unittest.TestCase):
    """Verifies Portuguese job scraping optimizations, language detection, and PT-PT CV & Cover Letter generation."""

    def setUp(self):
        from src.agents.application_agent import (
            generate_customized_cv,
            generate_customized_cover_letter,
        )
        from src.agents.matching.taxonomy import expand_role_synonyms, ROLE_SYNONYMS
        from src.agents.job_scraper_agent import optimize_query_for_source

        self.generate_customized_cv = generate_customized_cv
        self.generate_customized_cover_letter = generate_customized_cover_letter
        self.expand_role_synonyms = expand_role_synonyms
        self.ROLE_SYNONYMS = ROLE_SYNONYMS
        self.optimize_query_for_source = optimize_query_for_source

        self.mock_pt_job = {
            "id": "itjobs_9999",
            "title": "Engenheiro de Software Sénior",
            "company": "Critical TechWorks",
            "location": "Lisboa, Portugal (Híbrido)",
            "description": "Procuramos um Engenheiro de Software para integrar a nossa equipa de desenvolvimento. Experiência sólida em microsserviços, Python, Docker e Kubernetes.",
            "source": "ITJobs.pt",
            "matched_skills": ["Python", "Docker", "Kubernetes", "Microsserviços"],
            "key_reasons": ["Forte experiência em microsserviços e sistemas distribuídos"],
        }
        self.mock_profile = {
            "full_name": "Tiago Silva",
            "headline": "Engenheiro de Software Sénior",
            "location": "Porto, Portugal",
            "email": "tiago.silva@example.pt",
            "phone": "+351 912 345 678",
            "core_skills": ["Python", "Docker", "Kubernetes", "FastAPI", "PostgreSQL"],
            "experience_highlights": [
                "Liderou o desenvolvimento de microsserviços reduzindo a latência em 40%.",
                "Arquiteto de soluções cloud com 99,9% de disponibilidade operacional.",
            ],
        }

    def test_generate_customized_cv_pt_pt(self):
        cv = self.generate_customized_cv(self.mock_pt_job, self.mock_profile, language="pt-pt")
        self.assertIn("# TIAGO SILVA", cv)
        self.assertIn("Cargo Pretendido:", cv)
        self.assertIn("**Empresa Alvo:** Critical TechWorks", cv)
        self.assertIn("## RESUMO PROFISSIONAL", cv)
        self.assertIn("## COMPETÊNCIAS TÉCNICAS & HABILIDADES", cv)
        self.assertIn("## EXPERIÊNCIA PROFISSIONAL", cv)
        self.assertIn("## FORMAÇÃO ACADÉMICA & CERTIFICAÇÕES", cv)
        # Verify European Portuguese vocabulary
        self.assertIn("equipa", cv.lower())
        self.assertIn("utilizadores", cv.lower())

    def test_generate_customized_cover_letter_pt_pt(self):
        cl = self.generate_customized_cover_letter(self.mock_pt_job, self.mock_profile, language="pt-pt")
        self.assertIn("Tiago Silva", cl)
        self.assertIn("ASSUNTO: Candidatura à vaga de Engenheiro de Software Sénior (Referência ATS) — Critical TechWorks", cl)
        self.assertIn("Exma. Equipa de Recrutamento", cl)
        self.assertIn("equipa", cl.lower())
        self.assertIn("Com os melhores cumprimentos", cl)

    def test_role_synonyms_portuguese(self):
        expanded = self.expand_role_synonyms("engenheiro de software")
        expanded_lower = [e.lower() for e in expanded]
        self.assertTrue(any(k in expanded_lower for k in ["software engineer", "desenvolvedor", "programador"]))

        dev_expanded = self.expand_role_synonyms("desenvolvedor")
        dev_expanded_lower = [e.lower() for e in dev_expanded]
        self.assertTrue(any(k in dev_expanded_lower for k in ["software developer", "programador", "software engineer"]))

    def test_optimize_query_for_portuguese_portals(self):
        q_net = self.optimize_query_for_source("Software Engineer (Senior)", "Net-Empregos")
        self.assertEqual(q_net, "Engenheiro de Software")

        q_net_backend = self.optimize_query_for_source("Backend Developer", "NetEmpregos")
        self.assertEqual(q_net_backend, "Desenvolvedor Backend")

        q_itjobs = self.optimize_query_for_source("Software Engineer (Remote)", "ITJobs")
        self.assertEqual(q_itjobs, "Software Developer")


if __name__ == "__main__":
    unittest.main(verbosity=2)

