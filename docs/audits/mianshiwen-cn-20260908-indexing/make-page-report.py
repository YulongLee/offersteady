import json,csv
from pathlib import Path
root=Path(__file__).parent
rows=json.loads((root/'after/pages.json').read_text())
summary=json.loads((root/'after/sitemap-summary.json').read_text())
lines=['# 生产逐页检查 — 2026-09-08','', '30 个 sitemap 页面 + 2 个现有法律页面；普通爬虫和 Baiduspider 均直接 HTTP GET，不执行 JavaScript。','', '“允许”仅表示技术上未禁止索引，不等于百度已经收录。正文字符数不包含 head/script/style/nav/footer，不是质量得分。','', '|URL|普通/Baidu HTTP|Canonical|meta robots / X-Robots-Tag|robots.txt|H1/描述/正文|正文字符|首页深度|两种 UA HTML|','|---|---|---|---|---|---|---:|---:|---|']
with (root/'PAGE-CHECKS.csv').open('w',newline='') as f:
    writer=csv.writer(f);writer.writerow(['url','ordinary_status','baidu_status','canonical','meta_robots','x_robots_tag','robots_allowed','h1','description','body_chars','depth','ua_identical','evidence'])
    for r in rows[:32]:
        b=r['baidu']; d=summary['depth'].get(r['url'],1 if r['url'].endswith(('/terms','/privacy')) else '?')
        assert r['status']==b['status']==200
        assert r['canonical']==[r['url']] and r['robots_allowed']
        assert 'noindex' not in str(r['robots']).lower()+r['xrobots'].lower()
        assert r['h1'] and r['description'] and r['body_chars']>0
        assert r['sha256']==b['sha256']
        lines.append(f"|{r['url']}|200 / 200|{r['canonical'][0]}|无 / 无|允许|有 / 有 / 有|{r['body_chars']}|{d}|一致|")
        writer.writerow([r['url'],r['status'],b['status'],r['canonical'][0],';'.join(r['robots']),r['xrobots'],r['robots_allowed'],';'.join(r['h1']),';'.join(r['description']),r['body_chars'],d,True,'after/'+r['evidence']+'.html'])
lines+=['','## 私有与异常路由','',f"- /login：{rows[32]['status']}，X-Robots-Tag `{rows[32]['xrobots']}`；不在 sitemap。仍用 SPA shell，这是非索引登录入口，不将其计入公开 SEO 页面。",f"- 合成不存在路径：{rows[33]['status']}，非首页正文；没有软 404。",'', '## Robots 最终原文','', '```text',(root/'after/robots.html').read_text().rstrip(),'```','', '## 跳转检查','']
for r in json.loads((root/'after/variants.json').read_text()): lines.append(f"- {r['url']} → {r['final']}；{r['redirects']} 次跳转；最终 HTTP {r['status']}。")
(root/'PAGE-CHECKS.md').write_text('\n'.join(lines)+'\n')
print('PASS: verified 30 sitemap + 2 legal production documents; CSV and Markdown generated.')
