import urllib.request
import ssl
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from typing import List, Dict, Any

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8'
}

def fetch(url: str, timeout: int = 10) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()

# 1. PyJobs
def test_pyjobs():
    raw = fetch('https://www.pyjobs.com/').decode('utf-8', errors='ignore')
    soup = BeautifulSoup(raw, 'html.parser')
    jobs = []
    for a in soup.select('a[href*="/job/"]'):
        href = a.get('href', '')
        if not href or href == '/job/create' or 'create' in href:
            continue
        full_url = href if href.startswith('http') else f"https://www.pyjobs.com{href}"
        text = a.get_text(separator=' ', strip=True)
        if not text or len(text) < 4:
            continue
        # Extract title and company if formatted like "Role at Company"
        parts = text.split(' at ')
        title = parts[0].strip()
        company = parts[1].strip() if len(parts) > 1 else "PyJobs Employer"
        jobs.append({
            'title': title,
            'company': company,
            'location': 'Remote',
            'url': full_url,
            'source': 'PyJobs'
        })
    return jobs

# 2. UIUXJobsBoard
def test_uiuxjobsboard():
    raw = fetch('https://uiuxjobsboard.com/').decode('utf-8', errors='ignore')
    soup = BeautifulSoup(raw, 'html.parser')
    jobs = []
    for a in soup.select('a[href*="/job/"]'):
        href = a.get('href', '')
        if not href or 'post-a-job' in href:
            continue
        full_url = href if href.startswith('http') else f"https://uiuxjobsboard.com{href}"
        text = a.get_text(separator=' | ', strip=True)
        # Often formatted: "Company | is hiring | Title" or "Title | Company"
        parts = [p.strip() for p in text.split('|') if p.strip() and p.strip() != 'is hiring']
        if len(parts) >= 2:
            company = parts[0]
            title = parts[-1]
        elif len(parts) == 1:
            title = parts[0]
            company = "UI/UX Employer"
        else:
            continue
        jobs.append({
            'title': title,
            'company': company,
            'location': 'Remote',
            'url': full_url,
            'source': 'UIUXJobsBoard'
        })
    return jobs

# 3. DjangoProject
def test_djangoproject():
    raw = fetch('https://www.djangoproject.com/rss/community/jobs/')
    root = ET.fromstring(raw)
    jobs = []
    for it in root.findall('.//item'):
        title = it.find('title').text if it.find('title') is not None else ''
        link = it.find('link').text if it.find('link') is not None else ''
        pub_date = it.find('pubDate').text if it.find('pubDate') is not None else ''
        desc = it.find('description').text if it.find('description') is not None else ''
        # Often title is "Role at Company" or "Role (Company)"
        company = "Django Community"
        clean_title = title
        if ' at ' in title:
            p = title.split(' at ')
            clean_title, company = p[0].strip(), p[1].strip()
        elif ' - ' in title:
            p = title.split(' - ')
            clean_title, company = p[0].strip(), p[1].strip()
        jobs.append({
            'title': clean_title,
            'company': company,
            'location': 'Remote',
            'url': link,
            'date_posted': pub_date,
            'source': 'DjangoProject'
        })
    return jobs

# 4. RemotePython
def test_remotepython():
    raw = fetch('https://www.remotepython.com/jobs/').decode('utf-8', errors='ignore')
    soup = BeautifulSoup(raw, 'html.parser')
    jobs = []
    for it in soup.select('div.item'):
        h3 = it.select_one('h3')
        if not h3:
            continue
        a = h3.select_one('a')
        if not a:
            continue
        title = a.text.strip()
        href = a.get('href', '')
        full_url = href if href.startswith('http') else f"https://www.remotepython.com{href}"
        meta = it.select_one('.color-white-muted') or it.select_one('.meta')
        company = meta.text.strip() if meta else "RemotePython Employer"
        jobs.append({
            'title': title,
            'company': company,
            'location': 'Remote',
            'url': full_url,
            'source': 'RemotePython'
        })
    return jobs

# 5. 4DayWeek
def test_4dayweek():
    raw = fetch('https://4dayweek.io/api/jobs')
    data = json.loads(raw)
    jobs = []
    for j in data.get('jobs', []):
        title = j.get('title', '')
        slug = j.get('slug', '')
        url = f"https://4dayweek.io/job/{slug}" if slug else "https://4dayweek.io/remote-jobs"
        company = j.get('company_name') or "4DayWeek Employer"
        locs = j.get('locations')
        location = ", ".join(locs) if isinstance(locs, list) and locs else "Remote (4-Day Week)"
        jobs.append({
            'title': title,
            'company': company,
            'location': location,
            'url': url,
            'source': '4DayWeek'
        })
    return jobs

# 6. RemoteGameJobs
def test_remotegamejobs():
    raw = fetch('https://remotegamejobs.com/').decode('utf-8', errors='ignore')
    soup = BeautifulSoup(raw, 'html.parser')
    jobs = []
    for a in soup.select('a[href*="/jobs/"]'):
        href = a.get('href', '')
        if not href or href == '/jobs' or href.endswith('/jobs/'):
            continue
        full_url = href if href.startswith('http') else f"https://remotegamejobs.com{href}"
        text = a.get_text(separator=' | ', strip=True)
        parts = [p.strip() for p in text.split('|') if p.strip()]
        if not parts:
            continue
        title = parts[0]
        company = parts[1] if len(parts) > 1 else "Remote Game Studio"
        jobs.append({
            'title': title,
            'company': company,
            'location': 'Remote',
            'url': full_url,
            'source': 'RemoteGameJobs'
        })
    return jobs

# 7. HeyMarketers
def test_heymarketers():
    raw = fetch('https://heymarketers.com/jobs/').decode('utf-8', errors='ignore')
    soup = BeautifulSoup(raw, 'html.parser')
    jobs = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        # External application links (greenhouse, lever, stripe, adyen, etc.)
        if any(h in href for h in ['greenhouse.io', 'lever.co', 'workable.com', 'stripe.com', 'adyen.com', 'jobs.personio']):
            text = a.get_text(separator=' | ', strip=True)
            parts = [p.strip() for p in text.split('|') if p.strip()]
            title = parts[0] if parts else "Marketing Role"
            company = parts[1] if len(parts) > 1 else "Hiring Company"
            jobs.append({
                'title': title,
                'company': company,
                'location': 'Remote',
                'url': href,
                'source': 'HeyMarketers'
            })
    return jobs

# 8. Twine
def test_twine():
    raw = fetch('https://www.twine.net/jobs/digital-marketers').decode('utf-8', errors='ignore')
    soup = BeautifulSoup(raw, 'html.parser')
    jobs = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if any(h in href for h in ['torchbox', 'careers.teksystems.com', 'greenhouse', 'lever', 'personio']):
            text = a.get_text(separator=' ', strip=True)
            if not text or text in ['View on site', 'Apply']:
                continue
            jobs.append({
                'title': text,
                'company': 'Twine Project Client',
                'location': 'Remote',
                'url': href,
                'source': 'Twine'
            })
    return jobs

# 9. BerlinStartupJobs
def test_berlinstartupjobs():
    raw = fetch('https://berlinstartupjobs.com/engineering/').decode('utf-8', errors='ignore')
    soup = BeautifulSoup(raw, 'html.parser')
    jobs = []
    for h in soup.select('h2, h3, .entry-title'):
        a = h.find('a')
        if not a:
            continue
        title = a.text.strip()
        href = a.get('href', '')
        if not href or 'berlinstartupjobs.com/engineering' == href.rstrip('/'):
            continue
        jobs.append({
            'title': title,
            'company': 'European Startup',
            'location': 'Remote / Hybrid',
            'url': href,
            'source': 'BerlinStartupJobs'
        })
    return jobs

# 10. PythonJobsGithub
def test_pythonjobsgithub():
    raw = fetch('https://pythonjobs.github.io/').decode('utf-8', errors='ignore')
    soup = BeautifulSoup(raw, 'html.parser')
    jobs = []
    for div in soup.select('div.job'):
        a_links = div.find_all('a', href=True)
        if not a_links:
            continue
        h = div.select_one('h1, h2, h3')
        title = h.text.strip() if h else a_links[0].text.strip()
        link = a_links[0]['href']
        full_url = link if link.startswith('http') else f"https://pythonjobs.github.io{link}"
        jobs.append({
            'title': title if title and title != 'Read more' else 'Python Engineer',
            'company': 'Python Community',
            'location': 'Remote',
            'url': full_url,
            'source': 'PythonJobsGithub'
        })
    return jobs

# 11. Nodesk
def test_nodesk():
    raw = fetch('https://nodesk.co/remote-jobs/index.xml')
    root = ET.fromstring(raw)
    jobs = []
    for it in root.findall('.//item'):
        title = it.find('title').text if it.find('title') is not None else ''
        link = it.find('link').text if it.find('link') is not None else ''
        pub_date = it.find('pubDate').text if it.find('pubDate') is not None else ''
        company = "Nodesk Employer"
        clean_title = title
        if ' at ' in title:
            p = title.split(' at ')
            clean_title, company = p[0].strip(), p[1].strip()
        jobs.append({
            'title': clean_title,
            'company': company,
            'location': 'Remote',
            'url': link,
            'date_posted': pub_date,
            'source': 'Nodesk'
        })
    return jobs

# 12. DesignJobsBoard
def test_designjobsboard():
    raw = fetch('https://designjobsboard.com/').decode('utf-8', errors='ignore')
    soup = BeautifulSoup(raw, 'html.parser')
    jobs = []
    for a in soup.select('a[href*="/jobs/"]'):
        href = a.get('href', '')
        if not href or href == 'https://designjobsboard.com/jobs/':
            continue
        # Get parent context
        p = a.find_parent('div') or a.find_parent('article') or a.parent
        p_text = p.get_text(separator=' | ', strip=True) if p else a.get_text(strip=True)
        parts = [x.strip() for x in p_text.split('|') if x.strip() and x.strip() != 'Apply Now']
        title = parts[0] if parts else "Design Role"
        jobs.append({
            'title': title,
            'company': 'Design Studio',
            'location': 'Remote',
            'url': href,
            'source': 'DesignJobsBoard'
        })
    return jobs

runners = [
    ('PyJobs', test_pyjobs),
    ('UIUXJobsBoard', test_uiuxjobsboard),
    ('DjangoProject', test_djangoproject),
    ('RemotePython', test_remotepython),
    ('4DayWeek', test_4dayweek),
    ('RemoteGameJobs', test_remotegamejobs),
    ('HeyMarketers', test_heymarketers),
    ('Twine', test_twine),
    ('BerlinStartupJobs', test_berlinstartupjobs),
    ('PythonJobsGithub', test_pythonjobsgithub),
    ('Nodesk', test_nodesk),
    ('DesignJobsBoard', test_designjobsboard),
]

total = 0
for name, runner in runners:
    try:
        res = runner()
        print(f"PASS: {name:18} -> {len(res):2d} jobs found. Top: {res[0]['title'][:50] if res else 'None'}")
        total += len(res)
    except Exception as e:
        print(f"FAIL: {name:18} -> Error: {e}")

print(f"\nTotal jobs across 12 platforms: {total}")

