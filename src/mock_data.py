"""
Mock data and simulated parsing/matching engine for Module 1.
"""

SAMPLE_RESUME = """ALEX MERCER
San Francisco, CA | alex.mercer.dev@example.com | github.com/alexmercer | linkedin.com/in/alex-mercer-ai

SUMMARY
Senior AI / Software Engineer with 6+ years of experience designing, architecting, and deploying production autonomous AI agent workflows, LLM applications, and scalable backend platforms. Proven track record leading multi-agent system implementations using Google Antigravity SDK, Gemini 1.5/2.0 APIs, LangChain, and vector retrieval pipelines.

CORE COMPETENCIES
- AI & Agentic Systems: Google Antigravity SDK, Gemini API, Multi-Agent Swarms, Tool Calling & Function Execution, RAG Pipelines
- Programming: Python, TypeScript, SQL, Bash
- Frameworks & Backends: FastAPI, Streamlit, Docker, PostgreSQL, Qdrant, Pinecone
- Cloud & Infrastructure: Google Cloud Platform (Cloud Run, Vertex AI, BigQuery), Docker, CI/CD, Git

EXPERIENCE
Staff AI Engineer | Apex Autonomous Labs | 2023 - Present
- Architected enterprise multi-agent research and automation pipelines using Google Antigravity and Gemini models, reducing analyst document turnaround by 65%.
- Implemented stateful conversational agents with dynamic tool selection and guardrails, handling over 250k daily queries with 99.4% uptime.
- Deployed real-time RAG infrastructure utilizing Qdrant vector database with hybrid dense/sparse search.

Senior Backend Engineer | CloudScale Systems | 2020 - 2023
- Built high-throughput microservices in Python (FastAPI) and Go handling 15k requests/sec.
- Mentored junior engineers, established automated CI/CD testing pipelines, and cut infrastructure costs by 28%.

EDUCATION & CERTIFICATIONS
- B.S. in Computer Science, University of California, Berkeley
- Google Cloud Professional Machine Learning Engineer
"""

SAMPLE_PARSED_PROFILE = {
    "full_name": "Alex Mercer",
    "headline": "Senior AI / Agentic Systems Engineer",
    "years_of_experience": "6+ years",
    "location": "San Francisco, CA (Open to Remote)",
    "summary": "Specialist in building multi-agent architectures, Google Antigravity integrations, and production LLM orchestration systems with robust backend backbones.",
    "core_skills": [
        "Google Antigravity SDK",
        "Gemini API & Function Calling",
        "Autonomous Agent Swarms",
        "Python (FastAPI, Streamlit)",
        "RAG & Vector DBs (Qdrant, Pinecone)",
        "GCP (Vertex AI, Cloud Run)",
        "System Architecture",
    ],
    "experience_highlights": [
        "Architected multi-agent research pipelines with 65% speedup at Apex Autonomous Labs.",
        "Built enterprise LLM tool-calling guardrails servicing 250k+ daily queries.",
        "Engineered high-throughput microservices handling 15,000 req/sec at CloudScale Systems.",
    ],
    "target_roles": [
        "Senior AI / Agentic Systems Engineer",
        "Lead Agentic Systems Architect",
        "LLM Platform Engineer",
        "Applied AI Research Engineer",
    ],
}

MOCK_SCRAPE_LOGS = [
    {"time": "00:01", "agent": "Discovery Agent", "message": "Initialized search targets across Google Jobs, RemoteOK, and Greenhouse ATS API endpoints..."},
    {"time": "00:02", "agent": "Scraper Agent", "message": "Crawled 42 active engineering postings matching 'Agentic AI' and 'LLM Platform'..."},
    {"time": "00:03", "agent": "Filter Agent", "message": "Filtered 24 postings meeting remote requirements, senior experience, and compensation floor..."},
    {"time": "00:04", "agent": "Semantic Matcher", "message": "Running deep embedding similarity between Alex Mercer's profile and extracted JD requirements..."},
    {"time": "00:05", "agent": "Scoring Agent", "message": "Evaluated Antigravity, Gemini API, and Multi-Agent alignment for top 6 candidates..."},
    {"time": "00:06", "agent": "Synthesis Agent", "message": "Finalized tailored match reports and interview readiness scores. Results ready!"},
]

MOCK_JOB_RESULTS = [
    {
        "id": "job-001",
        "title": "Lead Agentic Systems Engineer",
        "company": "CognitiveFlow AI",
        "location": "Remote (US/Global)",
        "job_type": "Full-time (Remote)",
        "salary": "$185,000 - $225,000",
        "fit_score": 97,
        "match_type": "Exceptional Match",
        "badge_color": "#16a34a",
        "posted": "1 day ago",
        "company_size": "50-100 employees",
        "description": "Lead the development of autonomous multi-agent systems for enterprise knowledge orchestration. You will design agent toolkits, manage memory hierarchies, and collaborate on cutting-edge LLM agent patterns.",
        "key_reasons": [
            "Direct alignment with Google Antigravity & multi-agent swarm architecture.",
            "Strong requirement for FastAPI and vector database production deployments.",
            "Matches your 6+ years seniority and desired compensation range.",
        ],
        "matched_skills": ["Google Antigravity", "Multi-Agent Systems", "Gemini API", "Python", "Qdrant", "FastAPI"],
        "missing_skills": ["Kubernetes Operator Development"],
        "apply_url": "https://www.google.com/search?q=Lead+Agentic+Systems+Engineer+jobs",
    },
    {
        "id": "job-002",
        "title": "Senior AI Platform Engineer",
        "company": "Synthetica Labs",
        "location": "San Francisco, CA / Remote",
        "job_type": "Full-time (Hybrid / Remote)",
        "salary": "$175,000 - $210,000",
        "fit_score": 93,
        "match_type": "Strong Match",
        "badge_color": "#2563eb",
        "posted": "3 days ago",
        "company_size": "200-500 employees",
        "description": "Build high-throughput RAG infrastructure and agentic API layers for commercial generative AI applications. Focus on low-latency streaming, structured output guarantees, and model governance.",
        "key_reasons": [
            "Your experience with 250k daily queries directly proves required scalability.",
            "Heavy emphasis on structured outputs and function calling protocols.",
            "Remote-friendly with competitive equity package.",
        ],
        "matched_skills": ["LLM Tool Calling", "Vector DBs", "Python", "Cloud Run / GCP", "RAG Pipelines"],
        "missing_skills": ["Rust (Nice-to-have)"],
        "apply_url": "https://www.google.com/search?q=Senior+AI+Platform+Engineer+jobs",
    },
    {
        "id": "job-003",
        "title": "Staff LLM & Agent Architect",
        "company": "Nexus Automata",
        "location": "Remote (Worldwide)",
        "job_type": "Full-time (100% Async Remote)",
        "salary": "$190,000 - $240,000",
        "fit_score": 91,
        "match_type": "Strong Match",
        "badge_color": "#2563eb",
        "posted": "Just now",
        "company_size": "25-50 employees",
        "description": "Architect autonomous AI workforces that self-correct, plan complex tasks, and interact with web APIs. Looking for engineers who live and breathe autonomous agent development.",
        "key_reasons": [
            "Direct need for multi-agent coordination frameworks and autonomous workflows.",
            "Your proven track record reducing analyst turnaround time by 65%.",
            "100% async remote work culture.",
        ],
        "matched_skills": ["Autonomous Agents", "Gemini Models", "Python", "Prompt Architecture", "Docker"],
        "missing_skills": ["GraphQL API design"],
        "apply_url": "https://www.google.com/search?q=Staff+LLM+Agent+Architect+jobs",
    },
    {
        "id": "job-004",
        "title": "Applied AI Research Engineer (Agentic)",
        "company": "DeepOrbit Technologies",
        "location": "Remote (US)",
        "job_type": "Full-time (Remote)",
        "salary": "$170,000 - $205,000",
        "fit_score": 88,
        "match_type": "High Match",
        "badge_color": "#d97706",
        "posted": "5 days ago",
        "company_size": "100-250 employees",
        "description": "Bridge the gap between state-of-the-art agent research and customer-facing products. Evaluate model capabilities, benchmark agent reasoning, and implement automated tool learning.",
        "key_reasons": [
            "Strong match on UC Berkeley CS foundation and GCP ML Engineer credentials.",
            "Focus on agent evaluation metrics and systematic testing pipelines.",
        ],
        "matched_skills": ["Gemini API", "Python", "Evaluation & Guardrails", "Multi-Agent Systems"],
        "missing_skills": ["PyTorch fine-tuning"],
        "apply_url": "https://www.google.com/search?q=Applied+AI+Research+Engineer+jobs",
    },
    {
        "id": "job-005",
        "title": "Senior Backend & AI Integration Engineer",
        "company": "Vanguard Data",
        "location": "Remote (US/Canada)",
        "job_type": "Full-time (Remote)",
        "salary": "$165,000 - $195,000",
        "fit_score": 85,
        "match_type": "High Match",
        "badge_color": "#d97706",
        "posted": "1 week ago",
        "company_size": "500+ employees",
        "description": "Integrate cutting-edge generative AI models into established enterprise data analytics pipelines. Ensure data privacy, low latency, and robust error handling.",
        "key_reasons": [
            "Direct match for FastAPI, GCP BigQuery, and enterprise security requirements.",
            "High reliability focus aligns with your 99.4% uptime background.",
        ],
        "matched_skills": ["Python", "FastAPI", "GCP", "PostgreSQL", "Docker"],
        "missing_skills": ["Apache Spark"],
        "apply_url": "https://www.google.com/search?q=Senior+Backend+AI+Integration+Engineer+jobs",
    },
]
