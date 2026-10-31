"""Synthetic safety regressions for offline seal verification and extraction."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch


TOOLS = Path(__file__).parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


verify = load('verify_snapshot', TOOLS/'verify_snapshot.py')
restore = load('cn_seal_restore_test', TOOLS/'restore_snapshot.py')


def archive(path, name, entry_type=tarfile.REGTYPE):
    with tarfile.open(path, 'w:gz') as output:
        member = tarfile.TarInfo(name)
        member.type = entry_type
        if entry_type in (tarfile.SYMTYPE, tarfile.LNKTYPE):
            member.linkname = '../outside'
        else:
            member.size = 9
        output.addfile(member, io.BytesIO(b'synthetic') if member.isfile() else None)


class SnapshotSafetyTests(unittest.TestCase):
    def test_runtime_paths_cannot_escape_or_include_other_scopes(self):
        for key in ('', '.', '../escape.txt', '/tmp/escape.txt', 'apps/backend/app/../../outside',
                    'other/secret.txt', 'apps/backend/app\\outside.py', '.git/config'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify.safe_relative(key, 'runtime')
        self.assertEqual(verify.safe_relative('apps/backend/app/a.py', 'runtime'), 'apps/backend/app/a.py')
        self.assertEqual(verify.safe_relative('assets/._a.js'), 'assets/._a.js')

    def test_archive_traversal_absolute_and_links_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'synthetic.tar.gz'
            for key, kind in (('../escape.txt', tarfile.REGTYPE), ('/tmp/escape.txt', tarfile.REGTYPE),
                              ('safe-link', tarfile.SYMTYPE), ('safe-hardlink', tarfile.LNKTYPE)):
                with self.subTest(key=key, kind=kind):
                    archive(path, key, kind)
                    with self.assertRaises(ValueError):
                        verify.archive_entries(path)

    def test_duplicate_normalized_archive_paths_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'synthetic.tar.gz'
            with tarfile.open(path, 'w:gz') as output:
                for key in ('safe.txt', './safe.txt'):
                    member = tarfile.TarInfo(key)
                    member.size = 9
                    output.addfile(member, io.BytesIO(b'synthetic'))
            with self.assertRaises(ValueError):
                verify.archive_entries(path)

    def test_containment_rejects_symlinked_parent_and_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'root'
            outside = Path(directory)/'outside'
            root.mkdir(); outside.mkdir()
            (outside/'sentinel').write_text('unchanged')
            (root/'link').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                verify.contained_path(root, 'link/sentinel')
            (root/'file').symlink_to(outside/'sentinel')
            with self.assertRaises(ValueError):
                verify.contained_path(root, 'file')

    def test_backend_manifest_traversal_cannot_read_or_write_outside(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source/repo'
            release = source/'releases/cn-20261101.1'
            output = root/'output/root'
            release.mkdir(parents=True)
            (source.parent/'escape.txt').write_bytes(b'synthetic outside sentinel')
            (release/'manifest.json').write_text('{}')
            (release/'backend-runtime-manifest.json').write_text(json.dumps({'../escape.txt': 'synthetic-hash'}))
            # Exercise the path guard even if an independent full verifier is bypassed.
            with patch.object(restore, 'verify', return_value={'passed': True}):
                with self.assertRaises(ValueError):
                    restore.restore('backend', output, release_root=release, repo_root=source)
            self.assertFalse((output.parent/'escape.txt').exists())
            self.assertFalse(output.exists())
            self.assertEqual((source.parent/'escape.txt').read_bytes(), b'synthetic outside sentinel')

    def test_nonempty_output_and_full_verification_failure_never_write(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'output'
            output.mkdir()
            (output/'sentinel').write_text('unchanged')
            with self.assertRaises(ValueError):
                restore.restore('backend', output)
            self.assertEqual((output/'sentinel').read_text(), 'unchanged')
            empty = Path(directory)/'empty'
            with patch.object(restore, 'verify', side_effect=ValueError('synthetic full verification failure')):
                with self.assertRaises(ValueError):
                    restore.restore('backend', empty)
            self.assertFalse(empty.exists())

    def test_complete_source_binding_refuses_tampered_readme(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            release = repo/'releases/cn-20261101.1'
            release.mkdir(parents=True)
            readme = release/'README.md'
            readme.write_text('synthetic original')
            manifest = {'version': 'cn-20261101.1', 'applicationSecretsIncluded': False, 'rawUserDataIncluded': False,
                        'sourceFiles': {'releases/cn-20261101.1/README.md': hashlib.sha256(readme.read_bytes()).hexdigest()}}
            (release/'manifest.json').write_text(json.dumps(manifest))
            readme.write_text('synthetic unexpected change')
            with self.assertRaisesRegex(ValueError, 'sealed_source_file_changed'):
                verify.verify(release_root=release, repo_root=repo)

    def test_complete_source_binding_refuses_unlisted_file(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            release = repo/'releases/cn-20261101.1'
            release.mkdir(parents=True)
            (release/'unexpected.txt').write_text('synthetic')
            (release/'manifest.json').write_text(json.dumps({'version': 'cn-20261101.1',
                'applicationSecretsIncluded': False, 'rawUserDataIncluded': False,
                'sourceFiles': {'scripts/synthetic.py': 'a'*64}}))
            with self.assertRaisesRegex(ValueError, 'release_file_scope_changed'):
                verify.verify(release_root=release, repo_root=repo)


if __name__ == '__main__':
    unittest.main(verbosity=2)
