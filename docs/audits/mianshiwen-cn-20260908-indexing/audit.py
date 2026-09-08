"""Bounded sequential curl audit; saves raw public evidence, never private APIs."""
import subprocess, json, time, hashlib, sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup

out = Path(__file__).parent / (sys.argv[1] if len(sys.argv) > 1 else 'before')
out.mkdir(parents=True, exist_ok=True)
base = 'https://mianshiwen.cn'
def fetch(url, name, ua='OfferSteadyTechnicalAudit/2.0'):
    time.sleep(.3)
    command = ['curl', '-sS', '-L', '--max-redirs', '4', '--connect-timeout', '5', '--max-time', '20', '-A', ua, '-D', str(out / (name+'.headers')), '-o', str(out / (name+'.html')), '-w', '%{json}', url]
    p = subprocess.run(command, capture_output=True, text=True)
    if p.returncode: return {'url':url, 'error':p.stderr.strip()}
    stats=json.loads(p.stdout); raw=(out/(name+'.html')).read_bytes()
    headers=(out/(name+'.headers')).read_text().split('\n\n')
    final_headers=next((v for v in reversed(headers) if v.startswith('HTTP/')), '')
    header_values={k.lower():v.strip() for line in final_headers.splitlines()[1:] if ':' in line for k,v in [line.split(':',1)]}
    soup=BeautifulSoup(raw,'html.parser')
    meta=lambda n: [e.get('content','') for e in soup.find_all('meta',attrs={'name':n})]
    links=[urljoin(stats['url_effective'],e['href']).split('#')[0] for e in soup.select('a[href]')]
    h1=[e.get_text(' ',strip=True) for e in soup.select('h1')]
    row={'url':url,'status':stats['http_code'],'final':stats['url_effective'],'redirects':stats['num_redirects'],'ttfb':stats['time_starttransfer'],'total':stats['time_total'],'title':soup.title.get_text() if soup.title else '', 'description':meta('description'),'canonical':[e.get('href') for e in soup.select('link[rel="canonical"]')],'robots':meta('robots'),'baiduspider_meta':meta('baiduspider'),'xrobots':header_values.get('x-robots-tag',''),'headers':header_values,'h1':h1,'links':links,'sha256':hashlib.sha256(raw).hexdigest(),'scripts':[e.get('src') for e in soup.select('script[src]')],'evidence':name}
    for e in soup.select('head,script,style,nav,footer'): e.decompose()
    body=soup.get_text(' ',strip=True)
    row.update(body=body,body_chars=len(body),body_hash=hashlib.sha256(body.encode()).hexdigest())
    return row

fetch(base+'/robots.txt','robots'); fetch(base+'/sitemap.xml','sitemap')
tree=ET.fromstring((out/'sitemap.html').read_bytes())
assert tree.tag=='{http://www.sitemaps.org/schemas/sitemap/0.9}urlset'
urls=[e.text for e in tree.findall('{*}url/{*}loc')]
robots=RobotFileParser(); robots.parse((out/'robots.html').read_text().splitlines())
rows=[]
for i,url in enumerate(urls + [base+'/terms',base+'/privacy',base+'/login',base+'/seo-audit-not-found-20260908']):
    assert urlparse(url).hostname=='mianshiwen.cn'
    a=fetch(url,f'{i:02d}-ordinary'); b=fetch(url,f'{i:02d}-baidu','Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)')
    a['baidu']=b; a['in_sitemap']=url in urls; a['robots_allowed']=robots.can_fetch('Baiduspider',url)
    rows.append(a)
    (out/'pages.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    print(url,a.get('status'),b.get('status'),a.get('body_chars'),a.get('canonical'),flush=True)
variants=[]
for host in ['http://mianshiwen.cn','http://www.mianshiwen.cn','https://www.mianshiwen.cn']:
    for path in ['/','/pricing']:
        variants.append(fetch(host+path,'variant-'+str(len(variants))))
(out/'variants.json').write_text(json.dumps(variants,ensure_ascii=False,indent=2))
depth={base+'/':0}
for _ in range(len(rows)):
    for row in rows:
        if row['url'] in depth:
            for link in row.get('links',[]):
                if link in urls and (link not in depth or depth[link]>depth[row['url']]+1): depth[link]=depth[row['url']]+1
(out/'sitemap-summary.json').write_text(json.dumps({'count':len(urls),'unique':len(set(urls)),'lastmod':[{'url':e.find('{*}loc').text,'lastmod':e.findtext('{*}lastmod')} for e in tree],'depth':depth,'orphans':[u for u in urls if u not in depth]},ensure_ascii=False,indent=2))
