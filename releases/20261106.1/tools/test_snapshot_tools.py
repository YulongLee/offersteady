"""Synthetic archives only. These tests never import the business app."""
from __future__ import annotations

import io
import json
from pathlib import Path
import tarfile

import pytest

import restore_snapshot as restore_tool
import verify_snapshot as tool


def write_archive(path, entries):
    with tarfile.open(path, 'w:gz') as archive:
        for name, data, kind in entries:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.mode = 0o4755
            member.size = len(data) if kind == tarfile.REGTYPE else 0
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                member.linkname = '/synthetic-outside'
            archive.addfile(member, io.BytesIO(data) if kind == tarfile.REGTYPE else None)


def seal_files(repo, release, components):
    files = {str(path.relative_to(repo)): tool.sha(path.read_bytes())
             for path in release.rglob('*') if path.is_file() and path.name != 'manifest.json'}
    data = {'version': tool.VERSION, 'applicationSecretsIncluded': False,
            'rawUserDataIncluded': False, 'productionChangesByGitSeal': False,
            'files': files, 'components': components}
    (release / 'manifest.json').write_text(json.dumps(data))
    return data


@pytest.fixture
def sealed(tmp_path):
    repo = tmp_path / 'repo'
    release = repo / 'releases' / tool.VERSION
    release.mkdir(parents=True)
    (release / 'README.md').write_text('Synthetic seal')
    components = {}
    for name in sorted(tool.COMPONENTS):
        directory = release / name
        directory.mkdir()
        key = 'assets/synthetic.js' if name.endswith('-web') else 'apps/backend/app/synthetic.py'
        data = ('synthetic:' + name).encode()
        archive = directory / 'runtime.tar.gz'
        inventory = directory / 'inventory.json'
        write_archive(archive, [(key, data, tarfile.REGTYPE)])
        inventory.write_text(json.dumps({key: tool.sha(data)}))
        components[name] = {'archive': str(archive.relative_to(repo)),
                            'inventory': str(inventory.relative_to(repo)),
                            'image': 'sha256:' + 'a' * 64, 'count': 1}
    seal_files(repo, release, components)
    return repo, release, components


def test_verify_complete_synthetic_six_component_seal(sealed):
    repo, release, _ = sealed
    result = tool.verify(release_root=release, repo_root=repo)
    assert result['passed'] and set(result['components']) == tool.COMPONENTS
    assert result['productionChanges'] == 0 and result['networkCalled'] is False


@pytest.mark.parametrize('component', sorted(tool.COMPONENTS))
def test_restore_only_chosen_component_without_privileged_modes(sealed, tmp_path, component):
    repo, release, _ = sealed
    output = tmp_path / 'out'
    result = restore_tool.restore(component, output, release_root=release, repo_root=repo)
    files = [path for path in output.rglob('*') if path.is_file()]
    assert result['restored'] and len(files) == 1
    assert files[0].read_bytes() == ('synthetic:' + component).encode()
    assert files[0].stat().st_mode & 0o7777 == 0o755


@pytest.mark.parametrize('kind,name', [
    (tarfile.REGTYPE, '../escape'), (tarfile.REGTYPE, '/absolute'),
    (tarfile.REGTYPE, 'assets/../../escape'), (tarfile.REGTYPE, 'assets\\escape'),
    (tarfile.REGTYPE, '.git/config'), (tarfile.SYMTYPE, 'assets/link'),
    (tarfile.LNKTYPE, 'assets/hard-link'), (tarfile.FIFOTYPE, 'assets/pipe'),
])
def test_unsafe_archive_is_rejected_before_output_creation(sealed, tmp_path, kind, name):
    repo, release, components = sealed
    target = repo / components['global-web']['archive']
    write_archive(target, [(name, b'synthetic', kind)])
    seal_files(repo, release, components)
    output = tmp_path / 'out'
    with pytest.raises(tool.VerificationError):
        restore_tool.restore('global-web', output, release_root=release, repo_root=repo)
    assert not output.exists() and not (tmp_path / 'escape').exists()


def test_duplicate_archive_member_is_rejected(sealed):
    repo, release, components = sealed
    target = repo / components['global-web']['archive']
    write_archive(target, [('assets/synthetic.js', b'a', tarfile.REGTYPE)] * 2)
    seal_files(repo, release, components)
    with pytest.raises(tool.VerificationError, match='duplicate_archive_entry'):
        tool.verify(release_root=release, repo_root=repo)


def test_file_directory_collision_is_rejected(sealed):
    repo, release, components = sealed
    target = repo / components['global-web']['archive']
    write_archive(target, [('assets', b'a', tarfile.REGTYPE), ('assets/file.js', b'b', tarfile.REGTYPE)])
    seal_files(repo, release, components)
    with pytest.raises(tool.VerificationError, match='collision'):
        tool.verify(release_root=release, repo_root=repo)


def test_inventory_contents_must_match_even_after_archive_hash_is_updated(sealed):
    repo, release, components = sealed
    target = repo / components['global-web']['archive']
    write_archive(target, [('assets/synthetic.js', b'changed', tarfile.REGTYPE)])
    seal_files(repo, release, components)
    with pytest.raises(tool.VerificationError, match='archive_runtime_source_changed'):
        tool.verify(release_root=release, repo_root=repo)


def test_source_hash_change_prevents_any_restore(sealed, tmp_path):
    repo, release, _ = sealed
    (release / 'README.md').write_text('changed after sealing')
    output = tmp_path / 'out'
    with pytest.raises(tool.VerificationError, match='sealed_file_changed'):
        restore_tool.restore('cn-backend', output, release_root=release, repo_root=repo)
    assert not output.exists()


@pytest.mark.parametrize('existing_kind', ['empty_directory', 'file', 'directory_with_content', 'symlink'])
def test_existing_output_is_not_adopted_or_overwritten(sealed, tmp_path, existing_kind):
    repo, release, _ = sealed
    output = tmp_path / 'out'
    if existing_kind == 'file':
        output.write_text('keep')
    elif existing_kind == 'symlink':
        output.symlink_to(tmp_path / 'missing')
    else:
        output.mkdir()
        if existing_kind == 'directory_with_content':
            (output / 'keep').write_text('keep')
    with pytest.raises(tool.VerificationError, match='output_must_not_exist'):
        restore_tool.restore('cn-backend', output, release_root=release, repo_root=repo)
    assert output.is_symlink() if existing_kind == 'symlink' else output.exists()
    if existing_kind == 'directory_with_content':
        assert (output / 'keep').read_text() == 'keep'


def test_symlinked_output_parent_is_rejected(sealed, tmp_path):
    repo, release, _ = sealed
    real = tmp_path / 'real'
    real.mkdir()
    (tmp_path / 'linked').symlink_to(real, target_is_directory=True)
    with pytest.raises(tool.VerificationError, match='output_parent_is_linked'):
        restore_tool.restore('global-web', tmp_path / 'linked' / 'out', release_root=release, repo_root=repo)
    assert not (real / 'out').exists()


def test_symlinked_source_is_rejected_even_when_bytes_match(sealed, tmp_path):
    repo, release, _ = sealed
    outside = tmp_path / 'outside'
    outside.write_text('Synthetic seal')
    (release / 'README.md').unlink()
    (release / 'README.md').symlink_to(outside)
    with pytest.raises(tool.VerificationError, match='symlink'):
        tool.verify(release_root=release, repo_root=repo)


@pytest.mark.parametrize('mutation', ['extra_file', 'missing_file', 'component_removed', 'flag_true', 'count_changed'])
def test_seal_scope_cannot_silently_change(sealed, mutation):
    repo, release, _ = sealed
    manifest = json.loads((release / 'manifest.json').read_text())
    if mutation == 'extra_file':
        (release / 'extra').write_text('not sealed')
    elif mutation == 'missing_file':
        (release / 'README.md').unlink()
    elif mutation == 'component_removed':
        del manifest['components']['global-web']
    elif mutation == 'flag_true':
        manifest['rawUserDataIncluded'] = True
    else:
        manifest['components']['global-web']['count'] = 2
    (release / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(tool.VerificationError):
        tool.verify(release_root=release, repo_root=repo)


def test_runtime_archive_cannot_include_configuration_or_user_uploads(sealed):
    repo, release, components = sealed
    target = repo / components['cn-backend']['archive']
    write_archive(target, [('.env', b'synthetic-only', tarfile.REGTYPE)])
    seal_files(repo, release, components)
    with pytest.raises(tool.VerificationError, match='runtime_path_outside_scope'):
        tool.verify(release_root=release, repo_root=repo)


def test_oversized_member_is_rejected_before_reading_data(tmp_path, monkeypatch):
    target = tmp_path / 'oversized.tar.gz'
    monkeypatch.setattr(tool, 'MAX_MEMBER_BYTES', 8)
    write_archive(target, [('assets/huge.js', b'synthetic', tarfile.REGTYPE)])
    with pytest.raises(tool.VerificationError, match='oversized_archive_entry'):
        tool.archive_entries(target)
