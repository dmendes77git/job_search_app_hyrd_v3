"""
Role, Tech Stack, Geographic, and Seniority Taxonomies.
Houses standardized synonym maps, technology dictionaries, and pre-compiled regex patterns.
"""

import re
from typing import Dict, List

# Industry-standard role synonym and equivalence mappings for query expansion
ROLE_SYNONYMS: Dict[str, List[str]] = {
    "ai engineer": [
        "machine learning engineer",
        "ml engineer",
        "llm engineer",
        "applied ai scientist",
        "genai engineer",
        "ai research engineer",
    ],
    "machine learning": [
        "ai engineer",
        "data scientist",
        "deep learning engineer",
        "mlops engineer",
        "applied scientist",
    ],
    "software engineer": [
        "software developer",
        "full stack engineer",
        "backend engineer",
        "systems engineer",
        "platform engineer",
    ],
    "full stack": [
        "fullstack engineer",
        "full-stack developer",
        "web engineer",
        "software engineer",
    ],
    "backend": [
        "server engineer",
        "distributed systems engineer",
        "backend developer",
        "api engineer",
    ],
    "frontend": [
        "front end engineer",
        "ui engineer",
        "web developer",
        "react developer",
    ],
    "devops": [
        "cloud engineer",
        "site reliability engineer",
        "sre",
        "platform engineer",
        "infrastructure engineer",
    ],
    "data engineer": [
        "analytics engineer",
        "big data engineer",
        "data platform engineer",
        "etl developer",
    ],
    "data scientist": [
        "machine learning scientist",
        "data analyst",
        "applied scientist",
        "statistician",
    ],
    "product manager": [
        "technical product manager",
        "product lead",
        "group product manager",
        "product owner",
    ],
}


def expand_role_synonyms(role_title: str) -> List[str]:
    """
    Expand a job role title to include common industry-standard synonyms and equivalences.
    """
    if not role_title:
        return []
    clean = role_title.strip()
    clean_lower = clean.lower()
    results = [clean]
    for key, syns in ROLE_SYNONYMS.items():
        if key in clean_lower:
            for s in syns:
                if s not in clean_lower:
                    results.append(s.title())
    return list(dict.fromkeys(results))


# Recognized technology stack keywords for tech stack alignment & gap extraction
COMMON_TECH_STACK_KEYWORDS: List[str] = [
    # Languages
    "python", "typescript", "javascript", "golang", "rust", "java", "c++", "c#", "ruby", "scala", "swift", "kotlin",
    # AI & ML
    "pytorch", "tensorflow", "scikit-learn", "llm", "rag", "langchain", "llamaindex", "huggingface", "transformers",
    "vector db", "pinecone", "weaviate", "qdrant", "milvus", "agentic", "agents", "openai", "gemini",
    # Web Frameworks
    "react", "next.js", "vue", "angular", "node.js", "django", "fastapi", "flask", "spring boot", "graphql", "rest api",
    # Cloud, DevOps & Containers
    "docker", "kubernetes", "k8s", "terraform", "aws", "gcp", "azure", "ci/cd", "github actions", "helm", "ansible",
    # Databases & Streaming
    "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch", "kafka", "flink", "spark", "snowflake", "bigquery", "dbt",
    # Architecture & Tools
    "microservices", "distributed systems", "linux", "git", "grpc", "agile",
]


# Pre-defined country and major global city synonyms for geographic matching
COUNTRY_SYNONYMS: Dict[str, List[str]] = {
    "germany": ["germany", "deutschland", "berlin", "munich", "münchen", "hamburg", "frankfurt", "cologne", "köln", "stuttgart", "düsseldorf", "freiburg", "de"],
    "united kingdom": ["united kingdom", "uk", "great britain", "england", "scotland", "wales", "london", "manchester", "birmingham", "edinburgh", "bristol", "cambridge", "oxford", "leeds", "gb"],
    "united states": ["united states", "usa", "us", "u.s.", "america", "new york", "san francisco", "california", "texas", "austin", "seattle", "boston", "chicago", "los angeles", "denver", "atlanta", "nyc", "sf", "florida", "miami"],
    "canada": ["canada", "toronto", "vancouver", "montreal", "ottawa", "calgary", "ontario", "quebec", "british columbia", "alberta", "ca"],
    "netherlands": ["netherlands", "holland", "amsterdam", "rotterdam", "utrecht", "hague", "eindhoven", "nl"],
    "france": ["france", "paris", "lyon", "toulouse", "marseille", "bordeaux", "nantes", "fr"],
    "spain": ["spain", "españa", "madrid", "barcelona", "valencia", "seville", "es"],
    "switzerland": ["switzerland", "schweiz", "suisse", "zurich", "zürich", "geneva", "genève", "basel", "lausanne", "ch"],
    "ireland": ["ireland", "dublin", "cork", "galway", "ie"],
    "australia": ["australia", "sydney", "melbourne", "brisbane", "perth", "au"],
    "sweden": ["sweden", "sverige", "stockholm", "gothenburg", "malmö", "se"],
    "denmark": ["denmark", "danmark", "copenhagen", "københavn", "dk"],
    "poland": ["poland", "polska", "warsaw", "warszawa", "krakow", "kraków", "wroclaw", "wrocław", "pl"],
    "austria": ["austria", "österreich", "vienna", "wien", "salzburg", "graz", "at"],
    "singapore": ["singapore", "sg"],
    "israel": ["israel", "tel aviv", "jerusalem", "il"],
    "japan": ["japan", "tokyo", "osaka", "jp"],
    "india": ["india", "bangalore", "bengaluru", "hyderabad", "pune", "mumbai", "delhi", "in"],
    "portugal": ["portugal", "lisbon", "lisboa", "porto", "braga", "coimbra", "aveiro", "faro", "funchal", "madeira", "açores", "acores", "oeiras", "cascais", "leiria", "sintra", "setúbal", "setubal", "pt"],
    "italy": ["italy", "italia", "milan", "rome", "it"],
    "norway": ["norway", "norge", "oslo", "no"],
    "finland": ["finland", "suomi", "helsinki", "fi"],
    "brazil": ["brazil", "brasil", "são paulo", "rio", "br"],
    "mexico": ["mexico", "méxico", "mexico city", "monterrey", "guadalajara", "mx"],
}

# Pre-compiled word-boundary regex patterns for high-frequency country matching
_COMPILED_COUNTRY_PATTERNS: Dict[str, List[re.Pattern]] = {
    country: [re.compile(r"\b" + re.escape(s) + r"\b", re.IGNORECASE) for s in syns]
    for country, syns in COUNTRY_SYNONYMS.items()
}

_STOPWORDS_LOCATION = {"remote", "worldwide", "global", "anywhere", "hybrid", "onsite", "site", "any"}
_SENIORITY_TOKENS = ["senior", "lead", "manager", "director", "head", "specialist", "coordinator", "officer", "executive", "vp", "staff", "principal"]
