import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
const dist=resolve(import.meta.dirname,'../dist');
const sitemap=readFileSync(resolve(dist,'sitemap.xml'),'utf8');
const urls=[...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m=>m[1]);
assert.equal(urls.length,30);
const titles=new Set();
for (const url of [...urls,'https://mianshiwen.cn/terms','https://mianshiwen.cn/privacy']) {
  const path=new URL(url).pathname;
  const file=path==='/'?'index.html':['/guide','/terms','/privacy'].includes(path)?path.slice(1)+'.html':'seo/'+path.split('/').at(-1)+'.html';
  const html=readFileSync(resolve(dist,file),'utf8');
  assert(html.includes(`rel="canonical" href="${url}"`),url);
  assert(!/noindex/i.test(html),url);
  assert.equal([...html.matchAll(/<h1[\s>]/g)].length,1,url);
  const title=html.match(/<title>([^<]+)<\/title>/)?.[1];
  assert(title&&!titles.has(title),url); titles.add(title);
  assert(/name="description"\s+content="[^"]+"/.test(html),url);
  assert(html.includes('<a '),url);
  for (const m of html.matchAll(/(?:src|href)="(\/assets\/[^"?]+\.(?:js|css))"/g)) assert(existsSync(resolve(dist,'.'+m[1])),m[1]);
}
console.log('PASS: 30 sitemap + 2 existing legal documents have own indexable metadata/H1, links and existing entry assets.');
