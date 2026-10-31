"""Synthetic public graphs; no production services, users or network."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('mock_graph',Path(__file__).with_name('build_web_release.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class GraphTests(unittest.TestCase):
    def setUp(self):
        self.original={
          'assets/main-old.js':b"import './mock-old.js';import './other-old.js';const css='mock-old.css';",
          'assets/mock-old.js':b"import './main-old.js';export const mock=1;",
          'assets/mock-old.css':b'.mock{color:red}',
          'assets/other-old.js':b"import './main-old.js';export const preserved='resume/multi-screen/SEO/state';",
          'assets/report-old.js':b'export const report=1;',
          'assets/main-old.css':b'.main{color:blue}',
          'assets/media.png':b'synthetic-media',
          'assets/._main-old.js':b'synthetic-metadata',
          'robots.txt':b'User-agent: *',
          'offersteady-build.json':json.dumps({'appEnv':'production','apiBaseUrl':'/','appVersion':'old'}).encode(),
        }
        for html in m.ACTIVE_HTML:self.original[html]=b'<title>SEO</title><script src="/assets/main-old.js"></script><link href="/assets/main-old.css">'
        self.patched={'assets/mock-old.js':"import './main-old.js';import './voice-source.js';export const mock=2;",'assets/mock-old.css':'.mock{color:red} .new{color:green}', 'assets/voice-source.js':'export const voice=1;'}
        self.report={'patchedOriginalModules':['assets/mock-old.js','assets/mock-old.css'],'addedSourceModules':['assets/voice-source.js'],'sourceFiles':{}}

    def build(self):return m.assemble(self.original,self.patched,self.report,'cn-mock-20261101.1')

    def test_cache_safe_cycle_reference_only_parent_and_retained_originals(self):
        result,manifest=self.build();mapping=manifest['moduleMapping'];inverse={v:k for k,v in mapping.items()}
        self.assertEqual(set(mapping),{'assets/main-old.js','assets/other-old.js','assets/mock-old.js','assets/mock-old.css','assets/voice-source.js'})
        for name,data in self.original.items():
            if name not in m.MUTABLE:self.assertEqual(result[name],data)
        self.assertEqual(m.rewrite(result[mapping['assets/other-old.js']].decode(),inverse),self.original['assets/other-old.js'].decode())
        self.assertEqual(set(manifest['modifiedOriginals']),m.MUTABLE)
        self.assertEqual(result['assets/report-old.js'],self.original['assets/report-old.js'])
        self.assertEqual(result['robots.txt'],self.original['robots.txt'])

    def test_rejects_nonproduction_configuration(self):
        self.original['offersteady-build.json']=b'{"appEnv":"development","apiBaseUrl":"/"}'
        with self.assertRaisesRegex(ValueError,'nonproduction'):self.build()

    def test_rejects_inactive_original_patch(self):
        self.patched['assets/report-old.js']='export const report=2;';self.report['patchedOriginalModules'].append('assets/report-old.js')
        with self.assertRaisesRegex(ValueError,'scope'):self.build()

    def test_rejects_unreported_extra_module(self):
        self.patched['assets/surprise-source.js']='export const x=1;'
        with self.assertRaisesRegex(ValueError,'scope'):self.build()

    def test_rejects_invalid_generated_javascript(self):
        self.patched['assets/voice-source.js']='export const broken = ;'
        with self.assertRaisesRegex(ValueError,'invalid generated'):self.build()

    def test_rejects_preview_marker(self):
        self.patched['assets/voice-source.js']="export const marker='data-local-preview';"
        with self.assertRaisesRegex(ValueError,'preview'):self.build()

    def test_rejects_release_and_collisions(self):
        with self.assertRaisesRegex(ValueError,'release'):m.mapping_for({'assets/a-old.js':'a'},{'assets/a-old.js'},'other')
        with patch.object(m,'sha',return_value='0'*64):
            with self.assertRaisesRegex(ValueError,'collision'):m.mapping_for({'assets/a-old.js':'a','assets/a-00000000.js':'b'},{'assets/a-old.js'},'cn-mock-20261101.1')

    def test_rejects_symlink_public_input(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'safe').write_text('synthetic');(root/'link').symlink_to(root/'safe')
            with self.assertRaisesRegex(ValueError,'symlink'):m.load_files(root)

if __name__=='__main__':unittest.main()
