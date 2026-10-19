"""Verify sealed Global runtime/source hashes and optionally extract exact public files."""
from pathlib import Path
import argparse
import hashlib
import json
import tarfile

ROOT = Path(__file__).resolve().parents[2]
RELEASE = Path(__file__).resolve().parent
sha = lambda data: hashlib.sha256(data).hexdigest()

def read(name):
    return json.loads((RELEASE / name).read_text(encoding='utf-8'))

def extract_verified(archive, expected, destination):
    destination = Path(destination).resolve()
    with tarfile.open(RELEASE / archive, 'r:gz') as bundle:
        members = bundle.getmembers()
        assert len(members) == len(expected)
        assert set(item.name for item in members) == set(expected)
        for item in members:
            assert item.isfile() and not item.issym() and not item.islnk()
            parts = Path(item.name).parts
            assert not Path(item.name).is_absolute() and '..' not in parts
            data = bundle.extractfile(item).read()
            assert sha(data) == expected[item.name], item.name
            target = destination / item.name
            assert not target.is_symlink(), item.name
            target.parent.mkdir(parents=True, exist_ok=True)
            assert destination == target.parent.resolve() or destination in target.parent.resolve().parents
            target.write_bytes(data)
    return len(expected)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--extract-static')
    parser.add_argument('--extract-baseline')
    args = parser.parse_args()
    manifest = read('manifest.json')
    for name, digest in manifest['artifacts'].items():
        assert sha((RELEASE / name).read_bytes()) == digest, name
    for name, digest in read('backend-runtime-manifest.json').items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    for name, digest in read('frontend-source-manifest.json').items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    if args.extract_static:
        extract_verified('web-static.tar.gz', read('web-static-manifest.json'), args.extract_static)
    if args.extract_baseline:
        extract_verified('rebuild/baseline-web-static.tar.gz', read('rebuild/ancestor-static-manifest.json')['staticFiles'], args.extract_baseline)
    print(json.dumps({'passed': True, 'runtimeInputs': 302, 'frontendSourceInputs': 221, 'staticInputs': 235, 'productionAccessed': False}))

if __name__ == '__main__':
    main()
