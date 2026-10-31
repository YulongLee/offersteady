"""Synthetic graph and byte-preservation regressions; no network or users."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from build_web_release import (ACTIVE_HTML, MUTABLE_ORIGINALS, assemble, executable_modules,
                               load_files, reachable, references, reverse_closure, rewrite,
                               versioned_mapping)


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.modules = {
            'assets/main-old.js': 'import "./auth-old.js";import "./child-old.js";',
            'assets/auth-old.js': 'export const token=1;',
            'assets/child-old.js': 'import "./main-old.js";export const page=1;',
            'assets/historical-old.js': 'import "./auth-old.js";',
        }

    def test_active_graph_excludes_retained_historical_entries(self):
        active = reachable(self.modules, {'assets/main-old.js'})
        self.assertEqual(active, set(self.modules)-{'assets/historical-old.js'})
        selected = {n: self.modules[n] for n in active}
        self.assertEqual(reverse_closure(selected, {'assets/auth-old.js'}), active)

    def test_preloader_reference_tables_participate_in_reverse_closure(self):
        self.modules['assets/table-old.js'] = 'const preload=["auth-old.js"];'
        self.assertIn('assets/table-old.js', reverse_closure(self.modules, {'assets/auth-old.js'}))

    def test_cycles_are_renamed_simultaneously_and_reversible(self):
        closure = reverse_closure(self.modules, {'assets/main-old.js'})
        mapping = versioned_mapping(self.modules, closure, 'cn-state-control-20261029.1')
        inverse = {new: old for old, new in mapping.items()}
        for name in closure:
            updated = rewrite(self.modules[name], mapping)
            self.assertFalse(references(updated, mapping))
            self.assertEqual(rewrite(updated, inverse), self.modules[name])

    def test_release_generation_changes_names(self):
        closure = {'assets/main-old.js'}
        self.assertNotEqual(versioned_mapping(self.modules, closure, 'cn-state-control-20261029.1'),
                            versioned_mapping(self.modules, closure, 'cn-state-control-20261029.2'))

    def test_missing_changed_module_rejected(self):
        with self.assertRaises(ValueError): reverse_closure(self.modules, {'assets/missing-old.js'})

    def test_empty_closure_rejected(self):
        with self.assertRaises(ValueError): reverse_closure(self.modules, set())

    def test_missing_entry_rejected(self):
        with self.assertRaises(ValueError): reachable(self.modules, {'assets/missing-old.js'})

    def test_unapproved_release_id_rejected(self):
        with self.assertRaises(ValueError): versioned_mapping(self.modules, {'assets/main-old.js'}, '../bad')

    def test_binary_apple_metadata_remains_nonexecutable(self):
        self.assertEqual(executable_modules({'assets/._main-old.js': b'\xff\0', 'assets/main-old.js': b'export{};'}),
                         {'assets/main-old.js': 'export{};'})


class AssemblyTests(unittest.TestCase):
    def setUp(self):
        self.original = {
            'assets/main-old.js': b'import "./auth-old.js";import "./child-old.js";',
            'assets/auth-old.js': b'export const auth=1;',
            'assets/child-old.js': b'import "./main-old.js";export const page=1;',
            'assets/historical-old.js': b'import "./auth-old.js";',
            'assets/main-old.css': b'body{color:white}',
            'seo/pricing.html': b'<h1>Existing public price</h1>',
            'sitemap.xml': b'<urlset/>',
            'offersteady-build.json': b'{"appEnv":"production","apiBaseUrl":"/","appVersion":"old"}',
        }
        for name in ACTIVE_HTML:
            self.original[name] = b'<html><h1>Existing SEO</h1><script type="module" src="/assets/main-old.js"></script><link rel="modulepreload" href="/assets/auth-old.js"><link rel="stylesheet" href="/assets/main-old.css"></html>'
        self.patched = {
            'assets/main-old.js': 'import "./auth-old.js";import "./child-old.js";import "./state-source.js";',
            'assets/auth-old.js': 'export const auth=2;',
            'assets/state-source.js': 'export const generation=0;',
        }
        self.report = {'patchedOriginalModules': ['assets/main-old.js', 'assets/auth-old.js'],
                       'addedSourceModules': ['assets/state-source.js'], 'sourceFiles': {}}

    def assemble(self):
        return assemble(self.original, self.patched, self.report, b'unchanged nginx')

    def test_original_assets_css_seo_and_historical_graph_exactly_retained(self):
        result, manifest = self.assemble()
        self.assertEqual(set(manifest['modifiedOriginals']), MUTABLE_ORIGINALS)
        for name, data in self.original.items():
            if name not in MUTABLE_ORIGINALS: self.assertEqual(result[name], data, name)
        self.assertNotIn('assets/historical-old.js', manifest['moduleMapping'])
        self.assertTrue(manifest['invariants']['nginxAndCspUnchanged'])

    def test_html_modification_reverses_to_exact_existing_bytes(self):
        result, manifest = self.assemble()
        inverse = {new: old for old, new in manifest['moduleMapping'].items()}
        for name in ACTIVE_HTML:
            self.assertEqual(rewrite(result[name].decode(), inverse).encode(), self.original[name])

    def test_business_environment_unchanged_except_public_version(self):
        result, _ = self.assemble()
        old, new = json.loads(self.original['offersteady-build.json']), json.loads(result['offersteady-build.json'])
        self.assertEqual(new.pop('appVersion'), 'cn-state-control-20261029.1')
        old.pop('appVersion'); self.assertEqual(old, new)

    def test_rollback_retains_old_entry_and_new_immutable_assets(self):
        result, manifest = self.assemble()
        self.assertEqual(set(manifest['rollbackInventory']), set(self.original) | set(manifest['newModules']))
        self.assertEqual(manifest['rollbackInventory']['index.html'], manifest['baselineInventory']['index.html'])
        self.assertNotEqual(manifest['inventory']['index.html'], manifest['rollbackInventory']['index.html'])

    def test_extra_patch_payload_rejected(self):
        self.patched['assets/unapproved.js'] = 'export{};'
        with self.assertRaises(ValueError): self.assemble()

    def test_patch_of_inactive_historical_module_rejected(self):
        self.report['patchedOriginalModules'].append('assets/historical-old.js')
        self.patched['assets/historical-old.js'] = 'export{};'
        with self.assertRaises(ValueError): self.assemble()

    def test_local_preview_marker_rejected(self):
        self.patched['assets/state-source.js'] += 'const bad="local-preview-synthetic";'
        with self.assertRaises(ValueError): self.assemble()

    def test_nonproduction_environment_rejected(self):
        self.original['offersteady-build.json'] = b'{"appEnv":"development","apiBaseUrl":"/"}'
        with self.assertRaises(ValueError): self.assemble()

    def test_added_module_cannot_overwrite_existing_public_file(self):
        self.original['assets/state-source.js'] = b'old static'
        with self.assertRaises(ValueError): self.assemble()

    def test_public_input_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary); (path/'regular').write_text('synthetic'); (path/'link').symlink_to(path/'regular')
            with self.assertRaises(ValueError): load_files(path)


if __name__ == '__main__': unittest.main(verbosity=2)
