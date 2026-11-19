import urllib.request
import ssl
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8'
}

def fetch(url):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        return r.read()

print("--- Testing Nodesk ---")
try:
    html = fetch('https://nodesk.co/remote-jobs/')
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.select('li.job, article.job, .job-item, a[href*="/remote-jobs/"]')
    print(f"Nodesk matches: {len(items)}")
    for it in items[:3]:
        print(" ", it.text.strip().replace('\n', ' ')[:100], it.get('href'))
except Exception as e:
    print("Nodesk error:", e)

print("\n--- Testing BerlinStartupJobs ---")
try:
    html = fetch('https://berlinstartupjobs.com/')
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.select('article, .product-listing-item, h2 a, h3 a')
    print(f"BerlinStartupJobs matches: {len(items)}")
    for it in items[:5]:
        print(" ", it.text.strip().replace('\n', ' ')[:100], it.get('href'))
except Exception as e:
    print("BerlinStartupJobs error:", e)

print("\n--- Testing StartupJobs_com ---")
try:
    html = fetch('https://startupjobs.com/')
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.select('.job-item, .job-listing, a[href*="/jobs/"]')
    print(f"StartupJobs_com matches: {len(items)}")
    for it in items[:3]:
        print(" ", it.text.strip().replace('\n', ' ')[:100], it.get('href'))
except Exception as e:
    print("StartupJobs_com error:", e)

print("\n--- Testing RemoteStack ---")
try:
    html = fetch('https://remotestack.io/')
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.select('a[href*="/job/"], a[href*="/jobs/"]')
    print(f"RemoteStack matches: {len(items)}")
    for it in items[:3]:
        print(" ", it.text.strip().replace('\n', ' ')[:100], it.get('href'))
except Exception as e:
    print("RemoteStack error:", e)

