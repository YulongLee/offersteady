import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('global136_web',Path(__file__).with_name('build_web.py'))
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)


class MetadataTests(unittest.TestCase):
    def source(self):
        return 'var downloads=['+','.join('{version:`1.3.5`,href:`/api/v1/web/downloads/desktop/'+n+'`}' for n in B.FILENAMES)+'];const billing="preserve";'

    def test_only_version_and_three_official_urls_change(self):
        old=self.source();new=B.patch_metadata(old)
        self.assertEqual(new.count('version:`1.3.6`'),3)
        self.assertTrue(new.endswith('const billing="preserve";'))
        self.assertEqual(new.replace('1.3.6','1.3.5'),old)

    def test_missing_duplicated_or_changed_download_url_rejected(self):
        for old in (self.source().replace(B.FILENAMES[0],'other.exe'),self.source()+B.FILENAMES[0],self.source().replace('version:`1.3.5`','version:`1.3.4`',1)):
            with self.assertRaises(AssertionError):B.patch_metadata(old)

    def test_unrelated_existing_136_version_is_not_silently_normalized(self):
        with self.assertRaises(AssertionError):B.patch_metadata(self.source()+' const unrelated={version:`1.3.6`};')

    def fixture(self):
        files={B.MAIN:self.source().encode(),'assets/child-a.js':('import "./'+Path(B.MAIN).name+'";export const quota="original";').encode(),
               'index.html':('<!-- homepage-downloads:start -->'+''.join('<a href="/api/v1/web/downloads/desktop/'+n+'">download</a>' for n in B.FILENAMES)+'<!-- homepage-downloads:end --><script type="module" src="/'+B.MAIN+'"></script><script type="module" src="/assets/child-a.js"></script>').encode(),
               'offersteady-global-build.json':b'{"productEdition":"global","appEnv":"production","apiBaseUrl":"/","commerceEnabled":true,"commerceProvider":"creem","appVersion":"old"}',
               'assets/retained-old.js':b'const archived="keep byte-identical";'}
        return files,{n:B.sha(b) for n,b in files.items()}

    def test_graph_reverse_closure_preserves_old_bytes_and_rollback(self):
        files,manifest=self.fixture();new,rollback,proof=B.assemble(files,manifest)
        self.assertEqual(proof['addedModules'],2)
        for n,b in files.items():
            self.assertEqual(rollback[n],b)
            if n.startswith('assets/'):self.assertEqual(new[n],b)
        self.assertTrue(set(files)<=set(new))
        child=proof['moduleMapping']['assets/child-a.js']
        self.assertIn(Path(proof['moduleMapping'][B.MAIN]).name,new[child].decode())
        self.assertIn('quota="original"',new[child].decode())

    def test_actual_inventory_drift_is_rejected(self):
        files,manifest=self.fixture();files['assets/retained-old.js']+=b'changed'
        with self.assertRaises(AssertionError):B.assemble(files,manifest)

    def test_non_global_build_marker_rejected(self):
        files,_=self.fixture();files['offersteady-global-build.json']=files['offersteady-global-build.json'].replace(b'global',b'cn')
        with self.assertRaises(AssertionError):B.assemble(files,{n:B.sha(b) for n,b in files.items()})


if __name__=='__main__':unittest.main()
