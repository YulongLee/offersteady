"""Restore one verified component to a new local directory; never deploy it."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from verify_snapshot import (COMPONENTS, RELEASE_ROOT, archive_entries, contained_path,
                             read_json, require, sha, verify)


def _new_output_path(output):
    output = Path(os.path.abspath(output))
    require(not output.exists() and not output.is_symlink(), 'output_must_not_exist')
    for parent in output.parents:
        require(not parent.is_symlink(), 'output_parent_is_linked')
        if parent.exists():
            require(parent.is_dir(), 'output_parent_not_directory')
    return output


def restore(component, output, *, release_root=RELEASE_ROOT, repo_root=None):
    require(component in COMPONENTS, 'unsupported_component')
    output = _new_output_path(output)
    release_root = Path(release_root)
    repo_root = Path(repo_root) if repo_root is not None else release_root.parents[1]
    # Every component/source/manifest is verified before creating any output.
    verify(release_root=release_root, repo_root=repo_root)
    manifest = read_json(release_root / 'manifest.json')
    metadata = manifest['components'][component]
    archive = contained_path(repo_root, metadata['archive'])
    require(sha(archive.read_bytes()) == manifest['files'][metadata['archive']], 'archive_checksum_changed')
    expected = read_json(contained_path(repo_root, metadata['inventory']))
    entries = archive_entries(archive, runtime=not component.endswith('-web'))
    require({key: sha(value[0]) for key, value in entries.items()} == expected, 'source_bytes_changed')
    # Check the destination again immediately before writes; never adopt or
    # clean a path another process has created.
    output = _new_output_path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    _new_output_path(output)
    output.mkdir(mode=0o755)
    for relative, (data, mode) in entries.items():
        path = contained_path(output, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
        path.chmod(mode)
    return {'restored': True, 'component': component, 'files': len(entries),
            'productionChanges': 0, 'dockerCalled': False, 'networkCalled': False,
            'userDataRestored': False, 'privateConfigurationRestored': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component', choices=sorted(COMPONENTS), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repo-root', type=Path)
    args = parser.parse_args()
    try:
        release = args.repo_root / 'releases' / RELEASE_ROOT.name if args.repo_root is not None else RELEASE_ROOT
        print(json.dumps(restore(args.component, args.output, release_root=release,
                                 repo_root=args.repo_root), separators=(',', ':')))
    except Exception:
        print(json.dumps({'restored': False, 'reason': 'offline_restore_refused'}))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
