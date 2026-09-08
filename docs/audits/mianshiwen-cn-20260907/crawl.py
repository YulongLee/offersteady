"""Read-only, single-worker audit of sitemap/public pages; never crawl private APIs."""
import json, time, hashlib
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree
import requests
from bs4 import BeautifulSoup

out = Path(__file__).parent
base = 'https://mianshiwen.cn'
s = requests.Session()
s.headers['User-Agent'] = 'OfferSteadyReadOnlySEOAudit/1.0'
response = s.get(base+'/sitemap.xml', timeout=15)
(out/'sitemap.xml').write_text(response.text)
urls = [e.text for e in ElementTree.fromstring(response.content).iter() if e.tag.endswith('}loc')]
urls += [base+'/terms',base+'/privacy',base+'/login',base+'/seo-audit-missing-20260907', 'https://www.mianshiwen.cn/', 'http://mianshiwen.cn/']
rows=[]
for i,url in enumerate(dict.fromkeys(urls)):
    if urlparse(url).hostname not in ['mianshiwen.cn','www.mianshiwen.cn']: continue
    time.sleep(1)
    try:
        start=time.monotonic(); r=s.get(url,timeout=15); elapsed=round(time.monotonic()-start,3)
        r.encoding='utf-8'
        html=BeautifulSoup(r.content,'html.parser')
        meta=lambda name: [e.get('content','') for e in html.select('meta[name="'+name+'"]')]
        schema=[]
        for e in html.select('script[type="application/ld+json"]'):
            try: schema.append(json.loads(e.string or e.get_text()))
            except Exception: schema.append({'invalid':True})
        links=[e.get('href') for e in html.select('a[href]')]
        for e in html.select('script,style,nav,footer'): e.decompose()
        body=html.get_text(' ',strip=True)
        row={'url':url,'final':r.url,'status':r.status_code,'seconds':elapsed,'title':html.title.get_text() if html.title else '', 'description':meta('description'),'canonical':[e.get('href') for e in html.select('link[rel="canonical"]')],'robots':meta('robots'),'xrobots':r.headers.get('X-Robots-Tag'),'h1':[e.get_text(' ',strip=True) for e in html.select('h1')], 'body_chars':len(body),'body_hash':hashlib.sha256(body.encode()).hexdigest(),'body':body,'schema':schema,'links':links,'redirects':[x.status_code for x in r.history]}
        (out/f'page-{i}.html').write_text(r.text)
        rows.append(row)
        print(json.dumps({k:row[k] for k in ['url','status','title','h1','body_chars']},ensure_ascii=False),flush=True)
    except Exception as e: rows.append({'url':url,'error':str(e)})
    (out/'pages.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
