"""
Discovery package for official company domains, career page URLs, and deep ATS links.
"""

from .domain_finder import (
    find_company_official_url,
    enrich_jobs_with_company_urls,
    is_blocked_domain,
    extract_root_domain,
    calculate_domain_relevance,
)
from .career_finder import (
    find_career_page,
    enrich_jobs_with_career_pages,
    is_ats_url,
    is_career_link,
    probe_heuristic_career_path,
)
from .deep_link_matcher import (
    find_direct_apply_link,
    verify_and_extract_direct_links,
    is_ats_or_direct_apply_link,
    calculate_title_match_score,
    extract_iframe_src,
)

__all__ = [
    "find_company_official_url",
    "enrich_jobs_with_company_urls",
    "is_blocked_domain",
    "extract_root_domain",
    "calculate_domain_relevance",
    "find_career_page",
    "enrich_jobs_with_career_pages",
    "is_ats_url",
    "is_career_link",
    "probe_heuristic_career_path",
    "find_direct_apply_link",
    "verify_and_extract_direct_links",
    "is_ats_or_direct_apply_link",
    "calculate_title_match_score",
    "extract_iframe_src",
]
