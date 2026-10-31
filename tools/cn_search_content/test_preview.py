"""Content and isolation acceptance checks for the sealed-static local candidate."""
import base64
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit
from build_preview import ALLOWED, MAIN, ROOT, RELEASE, assemble, baseline, replace_once, sha

ROUTES = {
    '/': 'index.html', '/guide': 'guide.html', '/terms': 'terms.html', '/privacy': 'privacy.html',
    **{'/'+name: 'seo/'+name+'.html' for name in ('features','guides','interview-questions','pricing','download','security','about','contact')},
}
for group, names in {
 'features': 'ai-interview-assistant realtime-interview screenshot-answer interview-review',
 'guides': 'audio-troubleshooting interview-preparation macos-permissions feishu-audio-setup tencent-meeting-audio-setup star-interview-answer self-introduction project-experience technical-interview common-interview-questions',
 'interview-questions': 'llm rag ai-agent java-backend frontend algorithms',
}.items():
    ROUTES.update({f'/{group}/{name}': f'seo/{name}.html' for name in names.split()})


class Document(HTMLParser):
    def __init__(self, data):
        super().__init__(); self.h1 = 0; self.ids = []; self.links = []; self.canonical = []; self.scripts = []; self._script = None
        self.feed(data)
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'h1': self.h1 += 1
        if 'id' in a: self.ids.append(a['id'])
        if tag == 'a' and 'href' in a: self.links.append(a['href'])
        if tag == 'link' and a.get('rel') == 'canonical': self.canonical.append(a['href'])
        if tag == 'script' and not a.get('src'): self._script = ''
    def handle_data(self, data):
        if self._script is not None: self._script += data
    def handle_endtag(self, tag):
        if tag == 'script' and self._script is not None:
            self.scripts.append(self._script); self._script = None


class PreviewAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = baseline(); cls.files, cls.manifest = assemble()

    def test_only_approved_content_files_change(self):
        self.assertEqual(self.files.keys(), self.original.keys())
        changed = {k for k in self.files if self.files[k] != self.original[k]}
        self.assertEqual(changed, ALLOWED)
        self.assertEqual(len(self.files), 328)
        for name in self.files.keys() - ALLOWED:
            self.assertEqual(sha(self.files[name]), sha(self.original[name]), name)

    def test_deployed_business_components_and_import_graph_remain(self):
        for feature in ('MockInterviewPage', 'ResumeOptimizerPage', 'WrittenMultiScreen', 'AnswerWorkspace', 'BillingPage'):
            names = [n for n in self.files if feature in n and n.endswith('.js')]
            self.assertTrue(names, feature)
            for name in names: self.assertEqual(self.files[name], self.original[name], name)
        # Reversing the copy-only edits must exactly recover the original entry.
        text = self.files[MAIN].decode()
        for item in reversed(json.loads((ROOT/'tools/cn_search_content/homepage-copy.json').read_text())):
            text = text.replace(item['new'], item['old'], 1)
        self.assertEqual(text.encode(), self.original[MAIN])

    def test_ambiguous_or_missing_runtime_anchor_is_refused(self):
        for text in ('absent', 'old old'):
            with self.assertRaises(ValueError): replace_once(text, 'old', 'new')

    def test_four_documents_structure_canonical_and_scripts(self):
        csp = (RELEASE/'nginx/default.conf').read_text()
        for url in ('/', '/features/realtime-interview', '/features/ai-interview-assistant', '/pricing'):
            name = ROUTES[url]; doc = Document(self.files[name].decode()); old = Document(self.original[name].decode())
            with self.subTest(url=url):
                self.assertEqual(doc.h1, 1); self.assertEqual(len(doc.ids), len(set(doc.ids)))
                self.assertEqual(doc.canonical, ['https://mianshiwen.cn'+url])
                self.assertEqual(doc.scripts, old.scripts)
                for script in doc.scripts:
                    json.loads(script)
                    self.assertNotIn('FAQPage', script)
                    token = 'sha256-'+base64.b64encode(__import__('hashlib').sha256(script.encode()).digest()).decode()
                    self.assertIn(token, csp)
                for href in doc.links:
                    parsed = urlsplit(href)
                    if parsed.scheme or parsed.netloc or not parsed.path.startswith('/'):
                        if href.startswith('#'): self.assertIn(href[1:], doc.ids)
                        continue
                    if parsed.path.startswith('/app') or parsed.path == '/login': continue
                    target = ROUTES.get(parsed.path.rstrip('/') or '/', parsed.path.lstrip('/'))
                    self.assertIn(target, self.files, href)
                    if parsed.fragment:
                        if target == 'guide.html':
                            # Existing guide chapter links are rendered from its lazy data.
                            self.assertIn(href, Document(self.original[name].decode()).links)
                            guide_names = re.findall(r'GuidePage-[A-Za-z0-9_-]+\.js', self.files[MAIN].decode())
                            self.assertTrue(guide_names)
                            guide_data = ''.join(self.files['assets/'+n].decode() for n in set(guide_names))
                            self.assertIn('id:`'+parsed.fragment+'`', guide_data, href)
                        else:
                            self.assertIn(parsed.fragment, Document(self.files[target].decode()).ids, href)

    def test_catalog_is_preserved_exactly_and_template_still_generates(self):
        def catalog(html):
            return html[html.index('<section class="article-section" id="current-plans"'):html.index('<section class="article-section" id="credits-or-membership"')]
        self.assertEqual(catalog(self.files['seo/pricing.html'].decode()), catalog(self.original['seo/pricing.html'].decode()))
        template = (ROOT/'apps/web/public/seo/pricing.html').read_text()
        self.assertEqual(template.count('<!-- PRODUCTION_PRICING -->'), 1)
        for text in ('会员每天免费 1 场','会员每天免费 3 次','100 积分/场','100 积分/次','北京时间每天 00:00','60 分钟'):
            self.assertIn(text, template)

    def test_homepage_copy_present_in_both_rendering_surfaces(self):
        for item in json.loads((ROOT/'tools/cn_search_content/homepage-copy.json').read_text()):
            self.assertIn(item['new'], self.files[MAIN].decode())
            if item['old'] in self.original['index.html'].decode():
                self.assertIn(item['new'], self.files['index.html'].decode())
        self.assertIn('合成说明示例', self.files['index.html'].decode())

    def test_robots_sitemap_and_business_bootstrap_are_unchanged(self):
        for name in ('robots.txt','sitemap.xml','offersteady-build.json','guide.html','terms.html','privacy.html'):
            self.assertEqual(self.files[name], self.original[name], name)
        self.assertFalse(self.manifest['deploymentReady']); self.assertTrue(self.manifest['localOnly'])


if __name__ == '__main__': unittest.main(verbosity=2)
