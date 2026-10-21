"""Restore verified bytes into an empty local directory; never deploy services."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from verify_snapshot import RELEASE_ROOT, archive_entries, contained_path, read_json, require, safe_relative, sha, verify


def restore(component, output, *, release_root=RELEASE_ROOT, repo_root=None):
    require(component in {'backend', 'material-worker', 'web'}, 'unsupported_component')
    require(not output.is_symlink() and (not output.exists() or output.is_dir() and not any(output.iterdir())), 'output_must_be_empty')
    repo_root = repo_root or release_root.parents[1]
    verify(release_root=release_root, repo_root=repo_root)
    manifest = read_json(release_root/'manifest.json')
    if component == 'backend':
        expected = read_json(release_root/'backend-runtime-manifest.json')
        files = {key: (contained_path(repo_root, key, 'runtime').read_bytes(),
                       contained_path(repo_root, key, 'runtime').stat().st_mode & 0o777) for key in expected}
    else:
        archive = 'material-worker-runtime.tar.gz' if component == 'material-worker' else 'web-static.tar.gz'
        expected = read_json(release_root/('material-worker-runtime-manifest.json' if component == 'material-worker' else 'web-static-manifest.json'))
        require(sha((release_root/archive).read_bytes()) == manifest['archives'][archive], 'archive_checksum_changed')
        files = archive_entries(release_root/archive)
    require({key: sha(value[0]) for key, value in files.items()} == expected, 'source_bytes_changed')
    for relative in files:
        safe_relative(relative, 'runtime' if component != 'web' else 'artifact')
    if component == 'web':
        files = {'html/'+key: value for key, value in files.items()}
        nginx = (release_root/'nginx/default.conf').read_bytes()
        require(sha(nginx) == manifest['web']['nginxSha256'], 'nginx_bytes_changed')
        files['nginx/default.conf'] = (nginx, int(manifest['web']['nginxMetadata']['mode'], 8))
    output.mkdir(parents=True, exist_ok=True)
    for relative, (data, mode) in files.items():
        path = contained_path(output, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
        path.chmod(mode)
    return {'restored': True, 'component': component, 'files': len(files),
            'productionChanges': 0, 'dockerCalled': False, 'userDataRestored': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--component', choices=('backend', 'material-worker', 'web'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repo-root', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(restore(args.component, args.output, repo_root=args.repo_root), separators=(',', ':')))
    except Exception:
        print(json.dumps({'restored': False, 'reason': 'offline_restore_refused'}))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
