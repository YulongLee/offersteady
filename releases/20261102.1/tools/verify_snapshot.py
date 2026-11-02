"""Verify the Git seal offline; never contact Docker, a service or a provider."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile


RELEASE_ROOT = Path(__file__).resolve().parents[1]
VERSION = '20261102.1'
PREFIX = 'releases/' + VERSION + '/'
COMPONENTS = frozenset(region + '-' + role for region in ('cn', 'global')
                       for role in ('backend', 'material-worker', 'web'))
MAX_MEMBER_BYTES = 80 * 1024 * 1024
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 10000


class VerificationError(ValueError):
    """Only fixed privacy-safe reasons leave the command-line boundary."""


def require(condition, reason):
    if not condition:
        raise VerificationError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate_json_key')
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_bytes(), object_pairs_hook=_unique_object)


def safe_relative(key, scope='artifact'):
    require(isinstance(key, str) and bool(key) and '\\' not in key
            and all(ord(char) >= 32 for char in key), 'unsafe_relative_path')
    path = PurePosixPath(key)
    require(not path.is_absolute() and '..' not in path.parts and str(path) != '.'
            and '.git' not in path.parts, 'unsafe_relative_path')
    if scope == 'runtime':
        require(str(path) == 'apps/backend/pyproject.toml' or any(str(path).startswith(prefix)
                for prefix in ('apps/backend/app/', 'ai/prompts/', 'apps/backend/migrations/')),
                'runtime_path_outside_scope')
    return str(path)


def contained_path(root, relative, scope='artifact'):
    relative = safe_relative(relative, scope)
    root = Path(root)
    require(not root.is_symlink(), 'snapshot_root_is_linked')
    path = root / relative
    require(path.resolve().is_relative_to(root.resolve()), 'resolved_path_outside_root')
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        require(not current.is_symlink(), 'snapshot_symlink_refused')
    return path


def checked_inventory(value, *, runtime=False):
    require(isinstance(value, dict) and value and len(value) <= MAX_ARCHIVE_MEMBERS,
            'inventory_missing_or_oversized')
    result = {}
    for key, checksum in value.items():
        name = safe_relative(key, 'runtime' if runtime else 'artifact')
        require(name == key and name not in result and isinstance(checksum, str)
                and re.fullmatch('[0-9a-f]{64}', checksum), 'inventory_entry_invalid')
        result[name] = checksum
    _check_file_tree(set(result))
    return result


def _check_file_tree(names):
    for key in names:
        require(not any(str(parent) in names for parent in PurePosixPath(key).parents
                        if str(parent) != '.'), 'archive_file_directory_collision')


def archive_entries(path, *, runtime=False):
    """Read only regular, bounded, unique, safe paths; never use extractall."""
    result, seen, directories = {}, set(), set()
    total = 0
    with tarfile.open(path, 'r:gz') as archive:
        for index, member in enumerate(archive, 1):
            require(index <= MAX_ARCHIVE_MEMBERS, 'archive_member_limit_exceeded')
            key = safe_relative(member.name, 'runtime' if runtime and not member.isdir() else 'artifact')
            require(key not in seen, 'duplicate_archive_entry')
            seen.add(key)
            require(member.isdir() or member.isfile(), 'unsafe_archive_entry')
            if member.isdir():
                directories.add(key)
                continue
            require(0 <= member.size <= MAX_MEMBER_BYTES, 'oversized_archive_entry')
            total += member.size
            require(total <= MAX_ARCHIVE_BYTES, 'archive_total_limit_exceeded')
            stream = archive.extractfile(member)
            require(stream is not None, 'archive_entry_unreadable')
            with stream:
                data = stream.read(member.size + 1)
            require(len(data) == member.size, 'truncated_archive_entry')
            # A restored source/static file has no setuid/setgid/sticky bits.
            mode = 0o755 if member.mode & 0o111 else 0o644
            result[key] = (data, mode)
    require(result, 'archive_empty')
    _check_file_tree(set(result))
    require(not any(key in result or any(str(parent) in result for parent in PurePosixPath(key).parents)
                    for key in directories), 'archive_file_directory_collision')
    return result


def verify(*, release_root=RELEASE_ROOT, repo_root=None):
    release_root = Path(release_root)
    repo_root = Path(repo_root) if repo_root is not None else release_root.parents[1]
    require(release_root.resolve() == (repo_root / PREFIX).resolve()
            and not release_root.is_symlink(), 'release_location_changed')
    manifest = read_json(contained_path(release_root, 'manifest.json'))
    require(isinstance(manifest, dict) and manifest.get('version') == VERSION, 'wrong_release')
    for flag in ('applicationSecretsIncluded', 'rawUserDataIncluded', 'productionChangesByGitSeal'):
        require(manifest.get(flag) is False, 'private_or_production_scope_refused')
    files = checked_inventory(manifest.get('files'))
    require(PREFIX + 'manifest.json' not in files, 'manifest_self_reference_refused')
    actual_release = set()
    for path in release_root.rglob('*'):
        require(not path.is_symlink(), 'snapshot_symlink_refused')
        if path.is_file() and path != release_root / 'manifest.json' and '__pycache__' not in path.parts and path.suffix != '.pyc':
            actual_release.add(str(path.relative_to(repo_root)))
    expected_release = {name for name in files if name.startswith(PREFIX)}
    require(actual_release == expected_release, 'release_file_scope_changed')
    for relative, checksum in files.items():
        path = contained_path(repo_root, relative)
        require(path.is_file() and sha(path.read_bytes()) == checksum, 'sealed_file_changed')
    components = manifest.get('components')
    require(isinstance(components, dict) and set(components) == COMPONENTS, 'component_scope_changed')
    counts = {}
    for name, component in components.items():
        require(isinstance(component, dict) and isinstance(component.get('image'), str)
                and re.fullmatch('sha256:[0-9a-f]{64}', component['image']), 'component_image_invalid')
        archive, inventory = component.get('archive'), component.get('inventory')
        require(isinstance(archive, str) and isinstance(inventory, str) and archive != inventory
                and archive in files and inventory in files, 'component_inputs_not_sealed')
        runtime = not name.endswith('-web')
        expected = checked_inventory(read_json(contained_path(repo_root, inventory)), runtime=runtime)
        require(type(component.get('count')) is int and component['count'] == len(expected), 'component_count_changed')
        actual = {key: sha(value[0]) for key, value in archive_entries(
                  contained_path(repo_root, archive), runtime=runtime).items()}
        require(actual == expected, 'archive_runtime_source_changed')
        counts[name] = len(actual)
    return {'passed': True, 'version': VERSION, 'sealedFiles': len(files), 'components': counts,
            'productionChanges': 0, 'dockerCalled': False, 'networkCalled': False,
            'privateConfigurationRead': False, 'userDataRead': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path)
    args = parser.parse_args()
    try:
        release = args.repo_root / 'releases' / VERSION if args.repo_root is not None else RELEASE_ROOT
        print(json.dumps(verify(release_root=release, repo_root=args.repo_root), separators=(',', ':')))
    except Exception:
        print(json.dumps({'passed': False, 'reason': 'offline_snapshot_verification_refused'}))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
