"""Assemble a local-only content delta over the verified CN Web snapshot."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / 'releases/cn-20261022.1'
OUTPUT = ROOT / 'artifacts/cn-search-content-20261026/candidate'
MAIN = 'assets/main-8b805158.js'
PAGES = ('seo/realtime-interview.html', 'seo/ai-interview-assistant.html')
FACTS = ('llms.txt', 'llms-full.txt', 'public-facts.json')
ALLOWED = {'index.html', MAIN, 'seo/pricing.html', *PAGES, *FACTS}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def baseline():
    expected = json.loads((RELEASE/'web-static-manifest.json').read_text())
    seal = json.loads((RELEASE/'manifest.json').read_text())
    archive = RELEASE/'web-static.tar.gz'
    if sha(archive.read_bytes()) != seal['archives'][archive.name]:
        raise ValueError('snapshot archive changed')
    result = {}
    with tarfile.open(archive) as handle:
        for entry in handle.getmembers():
            path = PurePosixPath(entry.name)
            if not entry.isfile() or path.is_absolute() or '..' in path.parts:
                raise ValueError('unsafe snapshot entry')
            if entry.name in result:
                raise ValueError('duplicate snapshot entry')
            result[entry.name] = handle.extractfile(entry).read()
    if {name: sha(data) for name, data in result.items()} != expected:
        raise ValueError('snapshot files changed')
    return result


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('homepage copy anchor is absent or ambiguous: '+old[:32])
    return text.replace(old, new, 1)


def assemble():
    original = baseline()
    candidate = dict(original)
    copies = json.loads((ROOT/'tools/cn_search_content/homepage-copy.json').read_text())
    main = original[MAIN].decode()
    index = original['index.html'].decode()
    source = (ROOT/'apps/web/src/App.tsx').read_text()
    for item in copies:
        main = replace_once(main, item['old'], item['new'])
        if source.count(item['new']) < 1 or item['old'] in source:
            raise ValueError('homepage source and runtime copy differ')
        if item['old'] in index:
            index = replace_once(index, item['old'], item['new'])
    candidate[MAIN] = main.encode()
    candidate['index.html'] = index.encode()
    for name in (*PAGES, *FACTS):
        candidate[name] = (ROOT/'apps/web/public'/name).read_bytes()
    # Keep the entire original generated catalog, including its historic timestamp.
    old_pricing = original['seo/pricing.html'].decode()
    start = old_pricing.index('<section class="article-section" id="current-plans"')
    end = old_pricing.index('<section class="article-section" id="credits-or-membership"')
    catalog = old_pricing[start:end]
    template = (ROOT/'apps/web/public/seo/pricing.html').read_text()
    pricing = replace_once(template, '<!-- PRODUCTION_PRICING -->', catalog)
    candidate['seo/pricing.html'] = pricing.encode()
    changed = sorted(name for name in original if original[name] != candidate[name])
    if not set(changed) <= ALLOWED or candidate.keys() != original.keys():
        raise ValueError('unexpected change outside four-page content delta')
    manifest = {
        'localOnly': True, 'baseTag': 'release-cn-20261022.1',
        'baseWebImage': 'sha256:407376001c127de09cbb93d6bd9ee5f30dcace2693eb0c60e51c22e27cc49c1f',
        'files': len(candidate), 'unchanged': len(candidate)-len(changed),
        'changes': {name: {'before': sha(original[name]), 'after': sha(candidate[name])} for name in changed},
        'homepageStrategy': 'guarded text-only delta; original module names/import graph preserved; local no-store required',
        'deploymentReady': False,
        'deploymentPrerequisite': 'fresh target-image verification, graph-aware cache-safe asset versioning and current catalog verification',
        'catalogTimestamp': re.search(r'<time datetime="([^"]+)"', catalog).group(1),
    }
    return candidate, manifest


def build():
    files, manifest = assemble()
    if OUTPUT.exists() and not (OUTPUT/'local-content-preview.json').is_file():
        raise ValueError('refusing non-preview output directory')
    (OUTPUT/'html').mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        target = OUTPUT/'html'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (OUTPUT/'local-content-preview.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'candidate': str(OUTPUT), 'files': manifest['files'], 'unchanged': manifest['unchanged'], 'changed': list(manifest['changes']), 'localOnly': True}, ensure_ascii=False))


if __name__ == '__main__':
    build()
