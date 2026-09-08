"""Correct requests' Latin-1 fallback offline; keep headers when collecting H1."""
import json,hashlib
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
p=Path(__file__).parent
rows=json.loads((p/'pages.json').read_text())
for i,r in enumerate(rows):
    f=p/f'page-{i}.html'
    if not f.exists(): continue
    text=f.read_text()
    try: text=text.encode('latin1').decode('utf8')
    except (UnicodeEncodeError,UnicodeDecodeError): pass
    f.write_text(text)
    h=BeautifulSoup(text,'html.parser')
    r.update(title=h.title.get_text() if h.title else '',h1=[e.get_text(' ',strip=True) for e in h.select('h1')],description=[e.get('content','') for e in h.select('meta[name="description"]')],images=[{'src':e.get('src'),'alt':e.get('alt'),'width':e.get('width'),'height':e.get('height')} for e in h.select('img')])
    r['schema']=[]
    for e in h.select('script[type="application/ld+json"]'):
        try:r['schema'].append(json.loads(e.get_text()))
        except Exception:r['schema'].append({'invalid':True})
    for e in h.select('script,style,nav,footer'):e.decompose()
    r['body']=h.get_text(' ',strip=True);r['body_chars']=len(r['body']);r['body_hash']=hashlib.sha256(r['body'].encode()).hexdigest()
    r['incoming']=sum(any(urljoin(other['url'],l)==r['url'] for l in other.get('links',[]) if l) for other in rows if other['url']!=r['url'])
(p/'pages.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
for r in rows:print(json.dumps({k:r.get(k) for k in ['url','status','title','h1','canonical','robots','xrobots','body_chars','incoming']},ensure_ascii=False))
