"""Build a minimal, cache-safe state-read delta over the verified active CN Web.

Only public byte inputs are accepted. This tool never deploys or reads private
configuration. The production controller separately verifies fresh ownership,
configuration, active-user gates, fixed images, and these complete inventories.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BASE_WEB_IMAGE = 'sha256:9261bdb414ae99bc16e3e7efbddef715f3ca461756ee02bc89cf2476d17b311b'
RELEASE_ID = 'cn-state-control-20261029.1'
ACTIVE_HTML = ('index.html', 'guide.html', 'privacy.html', 'terms.html')
MUTABLE_ORIGINALS = {*ACTIVE_HTML, 'offersteady-build.json'}
BASELINE_MANIFEST = ROOT/'docs/releases/cn-search-content-20261027.1/web-release-manifest.json'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_files(directory):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('invalid public input directory')
    result = {}
    for path in directory.rglob('*'):
        if path.is_symlink():
            raise ValueError('symlink public input rejected')
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = path.read_bytes()
    return result


def executable_modules(files):
    modules = {n: b.decode() for n, b in files.items()
               if n.startswith('assets/') and n.endswith('.js') and not PurePosixPath(n).name.startswith('._')}
    if len({PurePosixPath(n).name for n in modules}) != len(modules):
        raise ValueError('ambiguous executable basename')
    return modules


def references(text, names):
    return {name for name in names if PurePosixPath(name).name in text}


def reachable(modules, entries):
    pending, seen = set(entries), set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        if name not in modules:
            raise ValueError('missing executable dependency')
        seen.add(name)
        pending |= references(modules[name], modules)-seen
    return seen


def reverse_closure(modules, changed):
    if not changed or not set(changed) <= modules.keys():
        raise ValueError('changed module outside active graph')
    closure = set(changed)
    while True:
        expanded = closure | {n for n, text in modules.items() if references(text, closure)}
        if expanded == closure:
            return closure
        closure = expanded


def versioned_mapping(modules, closure, release_id):
    if not re.fullmatch(r'cn-state-control-\d{8}\.\d+', release_id):
        raise ValueError('invalid state-control release id')
    result = {}
    for name in sorted(closure):
        path = PurePosixPath(name)
        match = re.fullmatch(r'(.+)-[A-Za-z0-9_-]+\.js', path.name)
        if not match:
            raise ValueError('unsupported active module name')
        seed = (release_id+'\0'+name+'\0'+sha(modules[name].encode())).encode()
        result[name] = str(path.with_name(match[1]+'-'+sha(seed)[:8]+'.js'))
    if len(set(result.values())) != len(result) or set(result.values()) & modules.keys():
        raise ValueError('immutable module-name collision')
    return result


def rewrite(text, mapping):
    names = {PurePosixPath(old).name: PurePosixPath(new).name for old, new in mapping.items()}
    pattern = re.compile('|'.join(re.escape(n) for n in sorted(names, key=len, reverse=True)))
    return pattern.sub(lambda m: names[m[0]], text)


def assemble(original, patched, patch_report, nginx, release_id=RELEASE_ID):
    modules = executable_modules(original)
    entries = set().union(*(references(original[n].decode(), modules) for n in ACTIVE_HTML))
    active = reachable(modules, entries)
    changed = set(patch_report['patchedOriginalModules'])
    added = set(patch_report['addedSourceModules'])
    if set(patched) != changed | added or not changed <= active or added & set(original):
        raise ValueError('runtime patch scope changed')
    selected = {n: modules[n] for n in active}
    selected.update(patched)
    closure = reverse_closure(selected, changed | added)
    mapping = versioned_mapping(selected, closure, release_id)
    if set(mapping.values()) & set(original):
        raise ValueError('new asset collides with existing public byte')
    result = dict(original)
    for old, new in mapping.items():
        result[new] = rewrite(selected[old], mapping).encode()
    for name in ACTIVE_HTML:
        result[name] = rewrite(original[name].decode(), mapping).encode()
    build = json.loads(original['offersteady-build.json'])
    if build.get('appEnv') != 'production' or build.get('apiBaseUrl') != '/':
        raise ValueError('production Web environment changed')
    build['appVersion'] = release_id
    result['offersteady-build.json'] = (json.dumps(build, separators=(',', ':'))+'\n').encode()
    modified = {n for n in original if original[n] != result[n]}
    if modified != MUTABLE_ORIGINALS or not set(original) <= result.keys():
        raise ValueError('original public scope changed')
    for name in original:
        if name not in MUTABLE_ORIGINALS and result[name] != original[name]:
            raise ValueError('unchanged original byte drift')
    inverse = {new: old for old, new in mapping.items()}
    for old, new in mapping.items():
        if rewrite(result[new].decode(), inverse) != selected[old]:
            raise ValueError('module changed beyond approved patch and graph rewrite')
    final_modules = executable_modules(result)
    new_entries = set().union(*(references(result[n].decode(), final_modules) for n in ACTIVE_HTML))
    active_after = reachable(final_modules, new_entries)
    if active_after & set(mapping) or not set(mapping.values()) <= active_after:
        raise ValueError('new graph retains old mutable generation or disconnected module')
    for name in ACTIVE_HTML:
        if rewrite(result[name].decode(), inverse) != original[name].decode():
            raise ValueError('public HTML changed beyond resource references')
    for text in final_modules.values():
        if 'cn-state-read-scope-source.js' in text and text not in modules.values():
            raise ValueError('source module placeholder remains')
    for token in (b'data-local-preview', b'local-preview-synthetic', b'OfferSteadyLocalPreview/'):
        if any(token in data for data in result.values()):
            raise ValueError('local preview implementation leaked')
    manifest = {
        'schemaVersion': 1, 'releaseId': release_id, 'baseWebImage': BASE_WEB_IMAGE,
        'packageReady': True, 'liveGateRequired': True, 'productionWrites': 0,
        'files': len(result), 'originalFiles': len(original), 'unchangedOriginals': len(original)-len(modified),
        'inventory': {n: sha(b) for n, b in sorted(result.items())},
        'baselineInventory': {n: sha(b) for n, b in sorted(original.items())},
        'modifiedOriginals': {n: {'before': sha(original[n]), 'after': sha(result[n])} for n in sorted(modified)},
        'newModules': {new: {'from': old, 'sha256': sha(result[new])} for old, new in sorted(mapping.items())},
        'moduleMapping': mapping,
        'nginx': {'beforeSha256': sha(nginx), 'afterSha256': sha(nginx), 'changed': False},
        'invariants': {
            'allOriginalImmutableAssetsRetained': True, 'allPublicSeoBytesRetained': True,
            'htmlOnlyResourceReferenceChanges': True, 'nginxAndCspUnchanged': True,
            'newGraphHasNoOldGeneration': True, 'moduleReverseEquivalence': True,
            'activeModulesBefore': len(active), 'activeModulesAfter': len(active_after),
            'fullSourceAppBundleUsed': False,
        },
        'sourceFiles': patch_report['sourceFiles'],
        'rollbackInventory': {n: sha(b) for n, b in sorted((original | {new: result[new] for new in mapping.values()}).items())},
    }
    return result, manifest


def build(baseline, output, release_id=RELEASE_ID):
    baseline, output = Path(baseline), Path(output)
    expected = json.loads(BASELINE_MANIFEST.read_text())
    original = load_files(baseline/'html')
    if {n: sha(b) for n, b in original.items()} != expected['inventory'] or len(original) != 339:
        raise ValueError('live public baseline differs from recorded current Web')
    nginx = (baseline/'nginx/default.conf').read_bytes()
    if sha(nginx) != expected['nginx']['afterSha256']:
        raise ValueError('live nginx baseline differs from recorded current Web')
    if output.exists() and any(output.iterdir()):
        raise ValueError('refusing nonempty output directory')
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='offersteady-state-runtime-patch-') as temporary:
        command = ['node', str(Path(__file__).with_name('build_runtime_patch.mjs')), str(baseline/'html'), temporary]
        subprocess.run(command, cwd=ROOT, check=True)
        patch_report = json.loads((Path(temporary)/'patch-report.json').read_text())
        patched = {n: (Path(temporary)/n).read_text() for n in patch_report['patchedOriginalModules']+patch_report['addedSourceModules']}
    result, manifest = assemble(original, patched, patch_report, nginx, release_id)
    # Syntax-check the final relinked generation before emitting a ready package.
    # Parsing alone does not reject duplicate lexical declarations.
    for name in manifest['newModules']:
        checked = subprocess.run(['node', '--check', '--input-type=module'], input=result[name], capture_output=True)
        if checked.returncode != 0:
            raise ValueError('invalid generated JavaScript module: '+name)
    for name, data in result.items():
        target = output/'web/html'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (output/'web/nginx').mkdir(parents=True, exist_ok=True)
    (output/'web/nginx/default.conf').write_bytes(nginx)
    report_path = output/'web-patch-report.json'
    report_path.write_text(json.dumps(patch_report, ensure_ascii=False, indent=2)+'\n')
    manifest['patchReportSha256'] = sha(report_path.read_bytes())
    manifest['syntaxCheckedNewModules'] = len(manifest['newModules'])
    (output/'web-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'releaseId': release_id, 'files': len(result), 'newModules': len(manifest['newModules']),
                      'modifiedOriginals': sorted(manifest['modifiedOriginals']), 'nginxUnchanged': True}))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--release-id', default=RELEASE_ID)
    args = parser.parse_args()
    build(args.baseline, args.output, args.release_id)
