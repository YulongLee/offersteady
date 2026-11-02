"""Only Global 1.3.6 download metadata and cache-safe references; no build/network."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('global136_graph', ROOT/'tools/state_read_optimization/build_web_release.py')
G = importlib.util.module_from_spec(spec); spec.loader.exec_module(G)
RELEASE = 'global-performance-companion-20261102.1'
MAIN = 'assets/main-08d5d48b.js'
FILENAMES = ('OfferSteady-Companion-Global-Setup-1.3.5-Windows-x64.exe',
             'OfferSteady-Companion-Global-1.3.5-macOS-arm64.dmg',
             'OfferSteady-Companion-Global-1.3.5-macOS-x64.dmg')


def sha(data): return hashlib.sha256(data).hexdigest()


def patch_metadata(text):
    assert text.count('version:`1.3.5`') == 3, 'unexpected version fields'
    for name in FILENAMES: assert text.count(name) == 1, 'unexpected Global download metadata'
    result = text.replace('version:`1.3.5`','version:`1.3.6`')
    for name in FILENAMES: result = result.replace(name,name.replace('1.3.5','1.3.6'))
    restored = result.replace('version:`1.3.6`','version:`1.3.5`')
    for name in FILENAMES: restored = restored.replace(name.replace('1.3.5','1.3.6'),name)
    assert restored == text, 'metadata patch changed unrelated bytes'
    return result


def assemble(original, expected):
    assert {n:sha(b) for n,b in original.items()} == expected, 'actual Global baseline differs'
    modules = G.executable_modules(original)
    html = [n for n in original if n.endswith('.html') and not PurePosixPath(n).name.startswith('._')]
    entries = set().union(*(G.references(original[n].decode(),modules) for n in html))
    active = G.reachable(modules,entries)
    assert MAIN in active, 'approved main is not active'
    closure = G.reverse_closure({n:modules[n] for n in active},{MAIN})
    patched = {n:patch_metadata(modules[n]) if n == MAIN else modules[n] for n in closure}
    mapping = {n:str(PurePosixPath(n).with_name(PurePosixPath(n).stem+'-'+sha((RELEASE+'\0'+n+'\0'+patched[n]).encode())[:8]+'.js')) for n in sorted(closure)}
    assert len(set(mapping.values())) == len(mapping) and not set(mapping.values()) & set(original)
    result = dict(original)
    for old,new in mapping.items(): result[new] = G.rewrite(patched[old],mapping).encode()
    changed_html = []
    for n in html:
        text = G.rewrite(original[n].decode(),mapping)
        if n == 'index.html':
            assert text.count('<!-- homepage-downloads:start -->') == 1
            for name in FILENAMES:
                assert text.count(name) == 1, 'fallback link changed'
                text = text.replace(name,name.replace('1.3.5','1.3.6'))
        if text.encode() != original[n]: changed_html.append(n)
        result[n] = text.encode()
    marker = json.loads(original['offersteady-global-build.json'])
    assert marker['productEdition'] == 'global' and marker['appEnv'] == 'production' and marker['apiBaseUrl'] == '/'
    marker['appVersion'] = RELEASE
    result['offersteady-global-build.json'] = (json.dumps(marker,separators=(',',':'))+'\n').encode()
    inverse = {new:old for old,new in mapping.items()}
    for old,new in mapping.items(): assert G.rewrite(result[new].decode(),inverse) == patched[old]
    for n in html:
        restored = G.rewrite(result[n].decode(),inverse)
        if n == 'index.html':
            for name in FILENAMES: restored = restored.replace(name.replace('1.3.5','1.3.6'),name)
        assert restored.encode() == original[n], 'HTML changed outside references/downloads'
    mutable = set(changed_html) | {'offersteady-global-build.json'}
    assert all(result[n] == b for n,b in original.items() if n not in mutable)
    final_modules = G.executable_modules(result)
    new_entries = set().union(*(G.references(result[n].decode(),final_modules) for n in html))
    reachable = G.reachable(final_modules,new_entries)
    assert set(mapping.values()) <= reachable and not set(mapping) & reachable
    rollback = dict(original) | {n:result[n] for n in mapping.values()}
    evidence = {'releaseId':RELEASE,'baselineInventory':expected,
                'inventory':{n:sha(b) for n,b in sorted(result.items())},
                'rollbackInventory':{n:sha(b) for n,b in sorted(rollback.items())},
                'moduleMapping':mapping,'modifiedOriginals':sorted(mutable),
                'unchangedOriginalFiles':len(original)-len(mutable),
                'addedModules':len(mapping),'metadataOnly':True,'wholeSourceBuildUsed':False,
                'allOriginalImmutableBytesRetained':True,'nginxChanged':False}
    return result,rollback,evidence


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists(), 'output must be new'
    result,rollback,report = assemble(G.load_files(a.baseline),json.loads(a.manifest.read_text()))
    for folder,files in [('html',result),('rollback',rollback)]:
        for n,b in files.items():
            path=a.output/folder/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b)
    delta={n:b for n,b in result.items() if report['baselineInventory'].get(n) != sha(b)}
    for n,b in delta.items():
        path=a.output/'delta'/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b)
    for new in report['moduleMapping'].values():
        subprocess.run(['node','--check','--input-type=module'],input=result[new],capture_output=True,check=True)
    (a.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'files':len(result),'newModules':report['addedModules'],'modifiedOriginals':len(report['modifiedOriginals'])}))


if __name__ == '__main__': main()
