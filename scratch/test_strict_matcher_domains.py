import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from utils.keyword_matcher import is_job_matching_keyword

test_cases = [
    # AI / ML Engineering
    ("AI Engineer", "Senior AI Engineer", True),
    ("AI Engineer", "Machine Learning Scientist", True),
    ("AI Engineer", "LLM Applications Engineer", True),
    ("AI Engineer", "Marketing Program Manager", False),
    ("AI Engineer", "Mechanical Engineer - HVAC", False),
    ("AI Engineer", "Civil Engineer", False),

    # Digital Marketing
    ("Digital Marketing", "Head of Growth", True),
    ("Digital Marketing", "Digital Marketing Specialist", True),
    ("Digital Marketing", "SEO Content Manager", True),
    ("Digital Marketing", "Senior Python Backend Engineer", False),
    ("Digital Marketing", "Civil Engineer", False),

    # Product Design & UI/UX
    ("Product Design", "Senior Product Designer", True),
    ("UI/UX Designer", "Senior UX/UI Product Designer", True),
    ("UI/UX Designer", "Product UX Designer", True),
    ("Product Design", "Interior Designer", False),
    ("Product Design", "Senior Backend Engineer", False),

    # Frontend (React, Vue, Next.js)
    ("Frontend Developer", "Senior React Developer", True),
    ("Frontend Developer", "Senior Frontend Developer - TypeScript, React", True),
    ("React Developer", "React Native Developer (f/m/d)", True),
    ("Frontend Developer", "Pure Backend Developer", False),
    ("Frontend Developer", "DevOps Engineer", False),

    # Backend (FastAPI, Django, Flask, Python)
    ("Django Developer", "Senior Python Engineer", True),
    ("Backend FastAPI", "Backend Developer (Python) - GenAI & LLM Applications", True),
    ("FastAPI Developer", "FastAPI Backend Developer", True),
    ("FastAPI Developer", "Sales Executive", False),
    ("Python Backend", "Senior Python developer", True),
]

all_passed = True
for query, title, expected in test_cases:
    actual = is_job_matching_keyword(title=title, keyword=query)
    status = "PASS" if actual == expected else "FAIL"
    if status == "FAIL":
        all_passed = False
    print(f"[{status}] Query: '{query:20}' | Title: '{title:50}' | Expected: {expected} | Actual: {actual}")

print(f"\nFinal result: {'ALL PASSED!' if all_passed else 'SOME FAILED!'}")
assert all_passed

