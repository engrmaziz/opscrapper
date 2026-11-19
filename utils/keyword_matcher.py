"""
Intelligent keyword normalization, typo-correction, and job title matching utility.
Ensures scraper queries and job title filtering bring genuine, relevant job leads
matching the user's intended role without returning unrelated jobs (e.g. AI Engineer for marketing).
"""

import re
from typing import Any, Dict, List, Optional, Set

# Common job role typo corrections and alias mappings
KEYWORD_TYPO_MAP: Dict[str, str] = {
    "markter": "marketer",
    "markting": "marketing",
    "markiting": "marketing",
    "enginere": "engineer",
    "enginer": "engineer",
    "softare": "software",
    "sofware": "software",
    "developper": "developer",
    "devloper": "developer",
    "desiner": "designer",
    "desinger": "designer",
    "anlayst": "analyst",
    "managr": "manager",
    "manger": "manager",
}

# Role domain semantic token expansions
ROLE_DOMAINS: Dict[str, Set[str]] = {
    "marketing": {
        "marketing", "marketer", "growth", "seo", "sem", "content", "social media",
        "copywriter", "brand", "ppc", "advertising", "campaign", "digital marketing",
        "performance marketing", "crm", "email marketing", "inbound", "affiliate",
        "communications", "media manager", "traffic", "acquisition",
    },
    "sales": {
        "sales", "account executive", "bdr", "sdr", "business development", "account manager",
        "client partner", "commercial", "revenue",
    },
    "design": {
        "designer", "design", "ui", "ux", "product design", "graphic", "visual",
        "illustrator", "motion", "creative director",
    },
    "data": {
        "data", "analytics", "analyst", "data science", "data scientist", "bi",
        "machine learning", "ml", "ai", "deep learning", "nlp", "computer vision",
    },
    "software": {
        "software", "developer", "engineer", "frontend", "backend", "full stack",
        "fullstack", "devops", "cloud", "sre", "systems", "mobile", "ios", "android",
    },
    "product": {
        "product manager", "product owner", "program manager", "product lead", "head of product",
    },
}


def normalize_search_keyword(raw_keyword: str) -> str:
    """Normalizes the search keyword, repairing common typos and stripping noise.
    
    Examples:
        'digital markter' -> 'digital marketer'
        'AI  Enginere ' -> 'AI Engineer'
    """
    if not raw_keyword:
        return ""

    tokens = raw_keyword.strip().split()
    corrected_tokens = []
    for t in tokens:
        clean = re.sub(r"[^\w\-]", "", t.lower())
        if clean in KEYWORD_TYPO_MAP:
            corrected_tokens.append(KEYWORD_TYPO_MAP[clean])
        else:
            corrected_tokens.append(t)

    return " ".join(corrected_tokens).strip()


def extract_search_tokens(keyword: str) -> List[str]:
    """Extracts significant search tokens and stems for matching."""
    normalized = normalize_search_keyword(keyword).lower()
    tokens = [re.sub(r"[^\w]", "", t) for t in normalized.split()]
    tokens = [t for t in tokens if len(t) >= 2 and t not in {"and", "or", "the", "for", "with", "in", "of"}]
    return tokens


def get_role_domain(keyword: str) -> Optional[str]:
    """Identifies the general domain of the keyword (marketing, software, data, etc.)."""
    kw_lower = normalize_search_keyword(keyword).lower()
    for domain, terms in ROLE_DOMAINS.items():
        if any(term in kw_lower for term in terms):
            return domain
    return None


# Global negative noise patterns (never allowed for tech/creative/marketing queries)
GLOBAL_NEGATIVE_NOISE_RE = re.compile(
    r"\b(civil|mechanical|electrical|hvac|plumbing|plumber|nurse|nursing|doctor|physician|dentist|dental|hygienist|carpenter|driver|truck\s+driver|cleaner|janitor|warehouse|security\s+guard|cook|chef|cashier|retail\s+associate|receptionist)\b",
    re.I,
)

# Targeted Focus Domain Definitions
TARGET_DOMAINS = {
    "ai_ml": {
        "triggers": [
            r"\b(ai|artificial\s+intelligence|machine\s+learning|ml|deep\s+learning|nlp|llm|computer\s+vision|generative\s+ai|data\s+scientist|data\s+science|mlops|applied\s+ai)\b"
        ],
        "required_title": [
            r"\b(ai|artificial\s+intelligence|machine\s+learning|ml|deep\s+learning|nlp|llm|computer\s+vision|generative\s+ai|data\s+scientist|data\s+science|mlops|applied\s+ai|prompt\s+engineer)\b"
        ],
        "excluded_in_title": [
            r"\b(sales|account\s+executive|recruiter|hr|copywriter|content|marketing|civil|mechanical|electrical|hvac)\b"
        ],
    },
    "digital_marketing": {
        "triggers": [
            r"\b(marketing|marketer|growth|seo|sem|social\s+media|content\s+marketing|ppc|performance\s+marketing|email\s+marketing|copywriter|copywriting|media\s+buyer|digital\s+marketing)\b"
        ],
        "required_title": [
            r"\b(marketing|marketer|growth|seo|sem|social\s+media|content\s+marketing|ppc|performance\s+marketing|email\s+marketing|copywriter|copywriting|media\s+buyer|digital\s+marketer|campaign\s+manager|brand\s+manager)\b"
        ],
        "excluded_in_title": [
            r"\b(software\s+engineer|backend|frontend|devops|sre|cloud\s+engineer|qa\s+engineer|civil|mechanical|nurse|hardware)\b"
        ],
    },
    "design_ui_ux": {
        "triggers": [
            r"\b(ui\s*/?\s*ux|ui|ux|user\s+experience|user\s+interface|product\s+design|product\s+designer|visual\s+design|interaction\s+design|figma)\b"
        ],
        "required_title": [
            r"\b(ui\s*/?\s*ux|ui|ux|user\s+experience|user\s+interface|product\s+design(?:er)?|interaction\s+design(?:er)?|visual\s+design(?:er)?|figma|web\s+designer)\b"
        ],
        "excluded_in_title": [
            r"\b(interior|fashion|mechanical|civil|landscape|architectural|hardware|structural|backend)\b"
        ],
    },
    "frontend": {
        "triggers": [
            r"\b(frontend|front\-end|front\s+end|react|vue|angular|next\.?js|nextjs|web\s+developer|ui\s+engineer)\b"
        ],
        "required_title": [
            r"\b(frontend|front\-end|front\s+end|react(?:js)?|vue(?:js)?|angular|next\.?js|ui\s+engineer|ui\s+developer|web\s+developer|javascript|typescript)\b"
        ],
        "excluded_in_title": [
            r"\b(pure\s+backend|backend\s+only|devops|sre|database\s+administrator|dba|sysadmin|civil|mechanical|nurse)\b"
        ],
    },
    "backend": {
        "triggers": [
            r"\b(backend|back\-end|back\s+end|fastapi|django|flask|python\s+developer|python\s+engineer|api\s+developer)\b"
        ],
        "required_title": [
            r"\b(backend|back\-end|back\s+end|fastapi|django|flask|python|api\s+developer|software\s+engineer)\b"
        ],
        "excluded_in_title": [
            r"\b(civil|mechanical|electrical|hvac|nurse|sales|marketing|accountant|interior)\b"
        ],
    },
}


def is_job_matching_keyword(
    title: str,
    company: str = "",
    keyword: str = "",
    tags: Optional[List[str]] = None,
    description: str = "",
) -> bool:
    """Strict relevance evaluator: determines whether a job posting matches the searched role.
    
    Guarantees:
    - Searching 'digital marketer' will NEVER return unrelated roles like 'Senior AI Engineer'.
    - Searching 'AI Engineer' will NEVER return 'Mechanical Engineer - HVAC' or 'Civil Engineer'.
    - Searching 'Backend FastAPI' requires backend/python/fastapi and blocks frontend/sales.
    """
    if not keyword or not keyword.strip():
        return True

    title_clean = (title or "").lower().strip()
    if not title_clean:
        return False

    kw_normalized = normalize_search_keyword(keyword).lower()
    
    # 1. Exact phrase match in title (Immediate Acceptance)
    if kw_normalized in title_clean:
        return True

    # 2. Check for Global Physical/Noise exclusion (never allowed unless query itself explicitly contains it)
    if GLOBAL_NEGATIVE_NOISE_RE.search(title_clean):
        if not any(noise in kw_normalized for noise in ["civil", "mechanical", "electrical", "hvac", "nurse"]):
            return False

    # 3. Check domain-specific matching for primary focus areas
    matched_domain = None
    for d_name, d_cfg in TARGET_DOMAINS.items():
        if any(re.search(trig, kw_normalized, re.I) for trig in d_cfg["triggers"]):
            matched_domain = d_cfg
            break

    if matched_domain:
        # Check domain negative exclusions
        for ex in matched_domain["excluded_in_title"]:
            if re.search(ex, title_clean, re.I):
                # If negative matches, ensure it doesn't have an overriding strong positive
                strong_override = False
                for req in matched_domain["required_title"]:
                    if re.search(req, title_clean, re.I):
                        strong_override = True
                        break
                if not strong_override:
                    return False

        # If specific frameworks like fastapi/django/flask are queried, they must match
        for fw in ["fastapi", "django", "flask"]:
            if fw in kw_normalized:
                comb_text = f"{title_clean} {' '.join(tags or [])} {description[:300]}".lower()
                if fw not in comb_text and "python" not in title_clean:
                    return False

        # Must match at least one required domain title pattern
        for req in matched_domain["required_title"]:
            if re.search(req, title_clean, re.I):
                return True
        return False

    # 4. Strict general keyword matching
    tokens = [re.sub(r"[^\w]", "", t) for t in kw_normalized.split()]
    tokens = [t for t in tokens if len(t) >= 2 and t not in {"and", "or", "the", "for", "with", "in", "of"}]
    if not tokens:
        return True

    # Every significant token must match in title or combined tags
    combined = f"{title_clean} {' '.join(tags or [])}".lower()
    return all(t in combined for t in tokens)


def filter_jobs_by_keyword(
    jobs: List[Dict[str, Any]],
    keyword: str,
) -> List[Dict[str, Any]]:
    """Filters a list of scraped jobs using strict relevance evaluation.
    NEVER falls back to returning all unrelated jobs when no matches exist.
    """
    if not keyword or not keyword.strip() or not jobs:
        return jobs

    kw_norm = normalize_search_keyword(keyword)
    filtered = []
    for j in jobs:
        title = j.get("title", "")
        company = j.get("company", "")
        tags = j.get("tags") if isinstance(j.get("tags"), list) else None
        desc = j.get("description", "")
        if is_job_matching_keyword(title=title, company=company, keyword=kw_norm, tags=tags, description=desc):
            filtered.append(j)

    return filtered
