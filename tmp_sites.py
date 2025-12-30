import re
import requests
from urllib.parse import urljoin, urlparse

SITES = {
    'topky.sk': 'https://www.topky.sk/se/15/Prominenti',
    'pluska.sk': 'https://www1.pluska.sk/r/soubiznis',
    'refresher.sk': 'https://refresher.sk/osobnosti',
    'startitup.sk': 'https://www.startitup.sk/kategoria/kultura/',
}

def extract_hrefs(html):
    return re.findall(r"href=[\"\']([^\"\']+)", html, re.I)

def normalize(url, base):
    if not url:
        return None
    url = url.strip()
    if url.startswith('//'):
        url = 'https:' + url
    elif url.startswith('/'):
        url = urljoin(base, url)
    elif not url.startswith('http'):
        return None
    url = url.split('#')[0].split('?')[0]
    return url

for name, url in SITES.items():
    html = requests.get(url, headers={'User-Agent':'Mozilla/5.0'}).text
    hrefs = [normalize(h, url) for h in extract_hrefs(html)]
    hrefs = [h for h in hrefs if h]
    # keep only same domain
    keep = []
    for h in hrefs:
        if urlparse(h).hostname and name in urlparse(h).hostname:
            keep.append(h)
    uniq = []
    seen = set()
    for h in keep:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    print('\n===', name, '===')
    print('total hrefs', len(hrefs), 'domain hrefs', len(uniq))
    # show sample longest 10 (likely articles)
    uniq_sorted = sorted(uniq, key=len, reverse=True)
    for h in uniq_sorted[:10]:
        print(h)
