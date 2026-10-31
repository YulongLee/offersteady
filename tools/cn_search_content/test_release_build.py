"""Regression checks for cache-safe, baseline-preserving production assembly."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import subprocess
import unittest

from build_preview import MAIN, ROOT, baseline
from build_release import (ACTIVE_HTML, assemble_release, executable_modules, extend_csp,
                           reverse_reference_closure, rewrite_references, validate_pricing, stamp_sitemap, SITEMAP_TARGETS,
                           versioned_names)

NOW = datetime(2026, 10, 27, 3, 0, tzinfo=timezone.utc)
RELEASE_ID = 'cn-search-content-20261027.1'


def rendered_pricing():
    # Synthetic catalogue only; never a real user or payment fixture.
    payload = {
        'catalog': [
            {'id': 'synthetic-pass-1', 'displayName': '合成一天会员', 'kind': 'time_pass',
             'priceCents': 1990, 'catalogVersion': 1, 'durationDays': 1, 'knowledgeIndexAllowance': 0},
            {'id': 'synthetic-points', 'displayName': '合成积分包', 'kind': 'points_pack',
             'priceCents': 990, 'catalogVersion': 1, 'points': 100},
        ],
        'rates': {'catalogVersion': 1, 'answerPoints': 5, 'screenshotAnswerPoints': 15,
                  'writtenExamPoints': 100, 'realtimeMinutePoints': 10,
                  'knowledgeIndexMinimumPoints': 20, 'knowledgeIndexPointsPer1000Tokens': 20},
    }
    script = """import {renderPricing} from './apps/web/pricing-static.mjs';
import {readFileSync} from 'node:fs';
const p=JSON.parse(readFileSync(0,'utf8'));
process.stdout.write(renderPricing(readFileSync('apps/web/public/seo/pricing.html','utf8'),p,new Date('2026-10-27T03:00:00.000Z')));"""
    return subprocess.run(['node', '--input-type=module', '-e', script], cwd=ROOT,
                          input=json.dumps(payload), text=True, capture_output=True, check=True).stdout


class GraphRewriteTests(unittest.TestCase):
    def setUp(self):
        self.modules = {
            'assets/main-a1.js': 'import "./child-b2.js"; import "./core-c3.js";',
            'assets/child-b2.js': 'import {x} from "./main-a1.js"; export const y=1;',
            'assets/core-c3.js': 'export const x=1;',
            'assets/legacy-d4.js': 'import "./core-c3.js";',
        }

    def test_cycle_closure_contains_importers_but_not_unaffected_shared_runtime(self):
        closure = reverse_reference_closure(self.modules, {'assets/main-a1.js'})
        self.assertEqual(closure, {'assets/main-a1.js', 'assets/child-b2.js'})
        mapping = versioned_names(self.modules, closure, RELEASE_ID)
        rewritten = rewrite_references(self.modules['assets/main-a1.js'], mapping)
        self.assertNotIn('main-a1.js', rewritten)
        self.assertNotIn('child-b2.js', rewritten)
        self.assertIn('core-c3.js', rewritten)
        reverse = {v: k for k, v in mapping.items()}
        self.assertEqual(rewrite_references(rewritten, reverse), self.modules['assets/main-a1.js'])

    def test_dependency_table_references_are_relinked_too(self):
        modules = dict(self.modules, **{'assets/preload-e5.js': 'const dependencies=["main-a1.js"];'})
        self.assertIn('assets/preload-e5.js', reverse_reference_closure(modules, {'assets/main-a1.js'}))

    def test_generation_changes_and_invalid_scope_is_rejected(self):
        closure = reverse_reference_closure(self.modules, {'assets/main-a1.js'})
        self.assertNotEqual(versioned_names(self.modules, closure, RELEASE_ID),
                            versioned_names(self.modules, closure, 'cn-search-content-20261027.2'))
        with self.assertRaises(ValueError): versioned_names(self.modules, closure, '../../bad')
        with self.assertRaises(ValueError): reverse_reference_closure(self.modules, {'assets/missing.js'})

    def test_binary_apple_metadata_is_preserved_without_becoming_executable(self):
        files = {'assets/main-a1.js': b'export{};', 'assets/._main-a1.js': b'\xff\x00'}
        self.assertEqual(set(executable_modules(files)), {'assets/main-a1.js'})


class ProductionAssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pricing = rendered_pricing()
        cls.original = baseline()
        cls.files, cls.nginx, cls.manifest = assemble_release(cls.pricing, RELEASE_ID, now=NOW)

    def test_old_immutable_graph_is_exactly_retained_and_new_graph_is_consistent(self):
        self.assertEqual(len(self.original), 328)
        self.assertEqual(len(self.manifest['moduleMapping']), 11)
        self.assertEqual(len(self.files), 339)
        for name, data in self.original.items():
            if name.startswith(('assets/', 'media/')): self.assertEqual(self.files[name], data, name)
        self.assertEqual(self.files[MAIN], self.original[MAIN])
        mapping = self.manifest['moduleMapping']
        for name in ACTIVE_HTML:
            text = self.files[name].decode()
            self.assertIn(Path(mapping[MAIN]).name, text)
            self.assertNotIn(Path(MAIN).name, text)
        self.assertTrue(self.manifest['invariants']['moduleReverseEquivalence'])
        self.assertTrue(self.manifest['invariants']['newGraphHasNoOldGeneration'])

    def test_all_new_modules_have_valid_javascript_syntax(self):
        for path in self.manifest['newModules']:
            result = subprocess.run(['node', '--check', '--input-type=module'], input=self.files[path].decode(),
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, path+': '+result.stderr)

    def test_fresh_catalog_matches_template_and_stale_or_wrong_template_is_refused(self):
        self.assertNotEqual(self.files['seo/pricing.html'], self.pricing.encode())
        self.assertIn('2026年10月27日', self.files['seo/pricing.html'].decode())
        self.assertEqual(self.manifest['pricing']['sourceHtmlSha256'], __import__('hashlib').sha256(self.pricing.encode()).hexdigest())
        self.assertEqual(validate_pricing(self.pricing, now=NOW)['snapshotAt'], '2026-10-27T03:00:00.000Z')
        with self.assertRaises(ValueError): validate_pricing(self.pricing, now=NOW+timedelta(days=2))
        with self.assertRaises(ValueError): validate_pricing(self.pricing+'unapproved', now=NOW)
        with self.assertRaises(ValueError): validate_pricing(self.pricing.replace('data-catalog-fingerprint=', 'missing='), now=NOW)

    def test_nginx_change_is_additional_exact_inline_hashes_only(self):
        before=(ROOT/'releases/cn-20261022.1/nginx/default.conf').read_text()
        reduced=self.nginx
        for token in self.manifest['nginx']['addedScriptHashes']:
            self.assertIn("'"+token+"'", self.nginx)
            reduced=reduced.replace(" '"+token+"'", '', 1)
        self.assertEqual(reduced, before)
        self.assertNotIn("'unsafe-eval'", self.nginx)
        self.assertEqual(len(self.manifest['nginx']['addedScriptHashes']), 3)
        # Unchanged pages must not gain extra inline-script permissions.
        same={'same.html': b'<script type="application/ld+json">{"name":"old"}</script>'}
        self.assertEqual(extend_csp(before,same,original=same)[0],before)
        with self.assertRaises(ValueError): extend_csp(before, {'bad.html': b'<script>alert(1)</script>'})

    def test_sitemap_changes_only_four_existing_lastmod_dates(self):
        original=self.original['sitemap.xml']; published=self.files['sitemap.xml']
        self.assertEqual(published,stamp_sitemap(original,'2026-10-27'))
        before=re.findall(rb'<loc>(.*?)</loc>',original);after=re.findall(rb'<loc>(.*?)</loc>',published)
        self.assertEqual(before,after)
        self.assertEqual(published.count(b'<lastmod>2026-10-27</lastmod>'),4)
        self.assertEqual(self.manifest['sitemap']['updatedUrls'],list(SITEMAP_TARGETS))
        # Duplicate or absent target URLs must fail rather than update another entry.
        with self.assertRaises(ValueError):stamp_sitemap(original.replace(b'https://mianshiwen.cn/pricing',b'https://mianshiwen.cn/other'),'2026-10-27')
        duplicate=original.replace(b'</urlset>',b'<url><loc>https://mianshiwen.cn/pricing</loc><lastmod>2026-09-12</lastmod></url></urlset>')
        with self.assertRaises(ValueError):stamp_sitemap(duplicate,'2026-10-27')

    def test_build_version_changes_without_environment_or_business_config(self):
        old=json.loads(self.original['offersteady-build.json']); new=json.loads(self.files['offersteady-build.json'])
        self.assertEqual(new['appVersion'], RELEASE_ID)
        old.pop('appVersion');new.pop('appVersion');self.assertEqual(old,new)
        for name in ['robots.txt','seo/screenshot-answer.html','seo/interview-review.html']:
            self.assertEqual(self.files[name],self.original[name],name)
        self.assertTrue(self.manifest['liveGateRequired']);self.assertEqual(self.manifest['productionWrites'],0)


if __name__ == '__main__': unittest.main(verbosity=2)
