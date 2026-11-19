import urllib.request
import ssl
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

try:
    req = urllib.request.Request('https://nodesk.co/remote-jobs/index.xml', headers=headers)
    with urllib.request.urlopen(req, timeout=6, context=ctx) as r:
        root = ET.fromstring(r.read())
        items = root.findall('.//item')
        print('=== Nodesk XML ===')
        print('Items:', len(items))
        for it in items[:5]:
            title = it.find('title').text if it.find('title') is not None else ''
            link = it.find('link').text if it.find('link') is not None else ''
            print(' ', title, link)
except Exception as e:
    print('Nodesk error:', e)

try:
    req = urllib.request.Request('https://www.remotecareers.com/', headers=headers)
    with urllib.request.urlopen(req, timeout=6, context=ctx) as r:
        soup = BeautifulSoup(r.read(), 'html.parser')
        jobs = soup.select('a[href*="/job/"]')
        print('=== RemoteCareers ===')
        print('Jobs:', len(jobs))
        for j in jobs[:5]:
            print(' ', j.text.strip().replace('\n', ' ')[:80], j.get('href'))
except Exception as e:
    print('RemoteCareers error:', e)

