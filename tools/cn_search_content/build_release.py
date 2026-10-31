"""Build a cache-safe Web-only release from the verified sealed CN static bytes.

This does not connect to production or deploy. The release controller must verify
its live baseline, current pricing and active-user gates separately.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
from xml.etree import ElementTree

from build_preview import FACTS, MAIN, PAGES, RELEASE, ROOT, assemble, baseline, sha

ACTIVE_HTML = ('index.html', 'guide.html', 'terms.html', 'privacy.html')
CONTENT_HTML = ('index.html', 'seo/pricing.html', *PAGES)
MUTABLE_ORIGINALS = {*ACTIVE_HTML, *PAGES, 'seo/pricing.html', *FACTS, 'offersteady-build.json', 'sitemap.xml'}
SITEMAP_TARGETS = ('https://mianshiwen.cn/', 'https://mianshiwen.cn/features/realtime-interview',
                   'https://mianshiwen.cn/features/ai-interview-assistant', 'https://mianshiwen.cn/pricing')
RELEASE_RE = re.compile(r'cn-search-content-\d{8}\.\d+')
MODULE_RE = re.compile(r'(?P<stem>.+)-[A-Za-z0-9_-]+\.js$')
SCRIPT_RE = re.compile(r'<script\b(?P<attrs>[^>]*)>(?P<body>.*?)</script\s*>', re.I | re.S)


def executable_modules(files):
    result = {}
    for name, data in files.items():
        if not name.startswith('assets/') or not name.endswith('.js') or PurePosixPath(name).name.startswith('._'):
            continue
        try:
            result[name] = data.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise ValueError('non-UTF8 executable module: '+name) from exc
    if len({PurePosixPath(n).name for n in result}) != len(result):
        raise ValueError('ambiguous executable basenames')
    return result


def module_references(text, modules):
    # Rolldown also keeps lazy-dependency names in a preloader table, so only
    # parsing static import declarations would miss required references.
    return {name for name in modules if PurePosixPath(name).name in text}


def reverse_reference_closure(modules, changed):
    if not changed or not set(changed) <= modules.keys():
        raise ValueError('changed module missing from verified input')
    closure = set(changed)
    while True:
        expanded = closure | {name for name, text in modules.items() if module_references(text, closure)}
        if expanded == closure:
            return closure
        closure = expanded


def versioned_names(modules, closure, release_id):
    if not RELEASE_RE.fullmatch(release_id):
        raise ValueError('invalid release id')
    mapping = {}
    for name in sorted(closure):
        path = PurePosixPath(name)
        match = MODULE_RE.fullmatch(path.name)
        if not match:
            raise ValueError('unsupported module name: '+name)
        # Cycles preclude final-content hash fixed points. This immutable name
        # derives from a release-scoped generation seed and the exact source.
        seed = (release_id+'\0'+name+'\0'+sha(modules[name].encode())).encode()
        mapping[name] = str(path.with_name(match['stem']+'-'+sha(seed)[:8]+'.js'))
    if len(set(mapping.values())) != len(mapping) or set(mapping.values()) & modules.keys():
        raise ValueError('module name collision')
    return mapping


def rewrite_references(text, mapping):
    replacements = {PurePosixPath(old).name: PurePosixPath(new).name for old, new in mapping.items()}
    if len(replacements) != len(mapping):
        raise ValueError('ambiguous reference rewrite')
    pattern = re.compile('|'.join(re.escape(name) for name in sorted(replacements, key=len, reverse=True)))
    return pattern.sub(lambda match: replacements[match[0]], text)


class PricingDocument(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.h1s = 0; self.fingerprints = []; self.times = []; self.canonicals = []
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'h1': self.h1s += 1
        if 'data-catalog-fingerprint' in a: self.fingerprints.append(a['data-catalog-fingerprint'])
        if tag == 'time' and 'datetime' in a: self.times.append(a['datetime'])
        if tag == 'link' and a.get('rel') == 'canonical': self.canonicals.append(a.get('href'))


def validate_pricing(html, *, now=None, template=None):
    template = template if template is not None else (ROOT/'apps/web/public/seo/pricing.html').read_text()
    marker = '<!-- PRODUCTION_PRICING -->'
    if template.count(marker) != 1:
        raise ValueError('pricing source marker missing or ambiguous')
    prefix, suffix = template.split(marker)
    if not html.startswith(prefix) or not html.endswith(suffix):
        raise ValueError('fresh pricing does not match the approved current template')
    doc = PricingDocument(html)
    if doc.h1s != 1 or doc.canonicals != ['https://mianshiwen.cn/pricing']:
        raise ValueError('pricing document identity changed')
    if len(doc.fingerprints) != 1 or not re.fullmatch(r'[0-9a-f]{64}', doc.fingerprints[0]):
        raise ValueError('fresh pricing fingerprint missing')
    generated = html[len(prefix):len(html)-len(suffix)] if suffix else html[len(prefix):]
    stamp = re.search(r'<time datetime="([^"]+)"', generated)
    if not stamp:
        raise ValueError('fresh pricing timestamp missing')
    at = datetime.fromisoformat(stamp[1].replace('Z', '+00:00'))
    if at.tzinfo is None:
        raise ValueError('pricing timestamp has no timezone')
    now = now or datetime.now(timezone.utc)
    age = (now-at).total_seconds()
    if not -60 <= age <= 86400:
        raise ValueError('pricing snapshot expired or from future')
    if '<!-- PRODUCTION_PRICING -->' in html or not re.search(r'data-product-id="[^"]+" data-price-cents="\d+"', generated):
        raise ValueError('pricing catalog not generated')
    return {'fingerprint': doc.fingerprints[0], 'snapshotAt': stamp[1], 'htmlSha256': sha(html.encode())}


def script_hashes(files):
    result = set()
    for name, data in files.items():
        if not name.endswith('.html') or PurePosixPath(name).name.startswith('._'):
            continue
        for match in SCRIPT_RE.finditer(data.decode('utf-8')):
            attrs, body = match['attrs'], match['body']
            if re.search(r'\bsrc\s*=', attrs, re.I) or not body.strip():
                continue
            if not re.search(r'type\s*=\s*["\']application/ld\+json["\']', attrs, re.I):
                raise ValueError('unapproved inline executable script: '+name)
            parsed = json.loads(body)
            if 'FAQPage' in body:
                raise ValueError('unapproved FAQPage schema')
            if not isinstance(parsed, (dict, list)):
                raise ValueError('invalid inline schema shape')
            result.add('sha256-'+base64.b64encode(__import__('hashlib').sha256(body.encode()).digest()).decode())
    return result


def extend_csp(nginx, files, *, original=None):
    pattern = re.compile(r'(set \$offersteady_csp ")([^"\n]+)(";)')
    matches = list(pattern.finditer(nginx))
    if len(matches) != 1:
        raise ValueError('CSP declaration absent or ambiguous')
    current = matches[0][2]
    if current.count("script-src ") != 1:
        raise ValueError('script-src declaration absent or ambiguous')
    # Validate supplied documents, but do not expand permissions for unchanged
    # baseline pages whose existing schema hash may already have been missing.
    script_hashes(files)
    changed = files if original is None else {n: b for n, b in files.items() if original.get(n) != b}
    required = script_hashes(changed)
    added = sorted(h for h in required if "'"+h+"'" not in current)
    updated = current.replace("script-src 'self'", "script-src 'self'"+''.join(" '"+h+"'" for h in added), 1)
    if added and updated == current:
        raise ValueError('expected script-src self anchor')
    result = nginx[:matches[0].start(2)]+updated+nginx[matches[0].end(2):]
    # The operation is additive exact hashes only. No other headers, routes,
    # proxy settings, security directives or former permitted hashes change.
    reduced = updated
    for h in added: reduced = reduced.replace(" '"+h+"'", '', 1)
    if reduced != current:
        raise ValueError('CSP changed beyond exact additional script hashes')
    return result, added


def stamp_sitemap(original, date):
    """Change the four approved lastmod values with byte-for-byte reversibility."""
    datetime.strptime(date, '%Y-%m-%d')
    text = original.decode('utf-8')
    ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    before = ElementTree.fromstring(text)
    entries = before.findall('s:url', ns)
    old = [(item.findtext('s:loc', namespaces=ns), item.findtext('s:lastmod', namespaces=ns)) for item in entries]
    locs = [url for url, _ in old]
    if len(locs) != len(set(locs)) or any(locs.count(url) != 1 for url in SITEMAP_TARGETS):
        raise ValueError('sitemap publication URL absent or ambiguous')
    old_dates = dict(old)
    patterns = {}
    for url in SITEMAP_TARGETS:
        pattern = re.compile(r'(<loc>'+re.escape(url)+r'</loc>\s*<lastmod>)(\d{4}-\d{2}-\d{2})(</lastmod>)')
        matches = list(pattern.finditer(text))
        if len(matches) != 1 or matches[0][2] != old_dates[url] or old_dates[url] == date:
            raise ValueError('sitemap publication date anchor changed')
        text, n = pattern.subn(lambda match: match[1]+date+match[3], text)
        if n != 1:
            raise ValueError('sitemap publication replacement count changed')
        patterns[url] = pattern
    after = ElementTree.fromstring(text)
    new = [(item.findtext('s:loc', namespaces=ns), item.findtext('s:lastmod', namespaces=ns)) for item in after.findall('s:url', ns)]
    expected = [(url, date if url in SITEMAP_TARGETS else lastmod) for url, lastmod in old]
    if new != expected:
        raise ValueError('sitemap entries changed outside publication dates')
    reversed_text = text
    for url, pattern in patterns.items():
        reversed_text, n = pattern.subn(lambda match: match[1]+old_dates[url]+match[3], reversed_text)
        if n != 1:
            raise ValueError('sitemap reverse replacement count changed')
    if reversed_text.encode() != original:
        raise ValueError('sitemap changed beyond four exact lastmod values')
    return text.encode()


def stamp_publication_metadata(content, release_id):
    """Apply only the approved publication date/local-label corrections."""
    if not RELEASE_RE.fullmatch(release_id):
        raise ValueError('invalid release id')
    date = datetime.strptime(release_id.split('-')[-1].split('.')[0], '%Y%m%d').date().isoformat()
    stamped = dict(content)
    for name in ('seo/pricing.html', *PAGES):
        text = stamped[name].decode()
        old_schema = '"dateModified":"2026-09-12"'
        if text.count(old_schema) != 1:
            raise ValueError('publication schema date anchor changed: '+name)
        changed = text.replace(old_schema, '"dateModified":"'+date+'"', 1)
        old_visible = ('<time datetime="2026-09-12">2026年9月12日</time>' if name == 'seo/pricing.html'
                       else '<time datetime="2026-09-12">2026-09-12</time>')
        if changed.count(old_visible) != 1:
            raise ValueError('publication visible date anchor changed: '+name)
        visible = (f'{int(date[:4])}年{int(date[5:7])}月{int(date[8:])}日' if name == 'seo/pricing.html' else date)
        changed = changed.replace(old_visible, f'<time datetime="{date}">{visible}</time>', 1)
        if '2026-09-12' in changed:
            raise ValueError('unexpected additional old publication date: '+name)
        stamped[name] = changed.encode()
    for name in ('llms.txt', 'llms-full.txt'):
        text = stamped[name].decode()
        old = '本地内容核对日期：2026-10-26'
        if text.count(old) != 1:
            raise ValueError('LLM publication label anchor changed: '+name)
        stamped[name] = text.replace(old, '内容核对日期：2026-10-26', 1).encode()
    facts = json.loads(stamped['public-facts.json'])
    facts['lastUpdated'] = date
    stamped['public-facts.json'] = (json.dumps(facts, ensure_ascii=False, indent=2)+'\n').encode()
    stamped['sitemap.xml'] = stamp_sitemap(stamped['sitemap.xml'], date)
    return stamped, date


def assert_release_invariants(original, content, result, mapping):
    if not set(original) <= result.keys():
        raise ValueError('sealed files removed')
    modified = {name for name in original if result[name] != original[name]}
    if not modified <= MUTABLE_ORIGINALS:
        raise ValueError('unapproved original file changed: '+str(sorted(modified-MUTABLE_ORIGINALS)))
    for name in original:
        if name.startswith(('assets/', 'media/')) and result[name] != original[name]:
            raise ValueError('sealed immutable asset changed: '+name)
    reverse = {new: old for old, new in mapping.items()}
    for old, new in mapping.items():
        text = result[new].decode()
        if rewrite_references(text, reverse) != content[old].decode():
            raise ValueError('module changed beyond approved content and import rewrites: '+old)
        if module_references(text, mapping):
            raise ValueError('new graph still references old generation: '+new)
    for name in ACTIVE_HTML:
        if module_references(result[name].decode(), mapping):
            raise ValueError('active HTML still references old generation: '+name)
    modules = executable_modules(result)
    entry = mapping[MAIN]
    pending, seen = [entry], set()
    while pending:
        name = pending.pop()
        if name in seen: continue
        seen.add(name)
        pending.extend(module_references(modules[name], modules)-seen)
    if set(mapping) & seen:
        raise ValueError('old entry generation reachable from new entry')
    if not set(mapping.values()) <= seen:
        raise ValueError('renamed module disconnected from new entry')
    for forbidden in (b'data-local-preview', b'local-preview-synthetic', b'OfferSteadyLocalPreview/'):
        if any(forbidden in value for value in result.values()):
            raise ValueError('local preview implementation leaked')
    return {'modifiedOriginals': sorted(modified), 'retainedImmutableAssets': sum(n.startswith(('assets/', 'media/')) for n in original),
            'activeReachableModuleCount': len(seen), 'newGraphHasNoOldGeneration': True,
            'allOriginalImmutableAssetsRetained': True, 'moduleReverseEquivalence': True}


def assemble_release(pricing_html, release_id, *, now=None):
    original = baseline()
    content, _preview_manifest = assemble()
    pricing = validate_pricing(pricing_html, now=now)
    content['seo/pricing.html'] = pricing_html.encode()
    content, publication_date = stamp_publication_metadata(content, release_id)
    pricing['sourceHtmlSha256'] = pricing['htmlSha256']
    pricing['htmlSha256'] = sha(content['seo/pricing.html'])
    modules = executable_modules(content)
    closure = reverse_reference_closure(modules, {MAIN})
    mapping = versioned_names(modules, closure, release_id)
    result = dict(original)
    for name in CONTENT_HTML + FACTS + ('sitemap.xml',):
        result[name] = content[name]
    for old, new in mapping.items():
        result[new] = rewrite_references(modules[old], mapping).encode()
    for name in ACTIVE_HTML:
        result[name] = rewrite_references(result[name].decode(), mapping).encode()
    build = json.loads(original['offersteady-build.json'])
    if build.get('appEnv') != 'production' or build.get('apiBaseUrl') != '/':
        raise ValueError('sealed production environment identity changed')
    build['appVersion'] = release_id
    result['offersteady-build.json'] = (json.dumps(build, separators=(',', ':'))+'\n').encode()
    nginx_before = (RELEASE/'nginx/default.conf').read_text()
    nginx, added_hashes = extend_csp(nginx_before, result, original=original)
    invariants = assert_release_invariants(original, content, result, mapping)
    changed = invariants['modifiedOriginals']
    manifest = {
        'schemaVersion': 1, 'releaseId': release_id, 'publicationDate': publication_date, 'baseTag': 'release-cn-20261022.1',
        'baseWebImage': 'sha256:407376001c127de09cbb93d6bd9ee5f30dcace2693eb0c60e51c22e27cc49c1f',
        'packageReady': True, 'liveGateRequired': True, 'productionWrites': 0,
        'generationNaming': '8hex sha256(releaseId + originalPath + sourceSha256); import cycles relinked simultaneously',
        'files': len(result), 'originalFiles': len(original), 'unchangedOriginals': len(original)-len(changed),
        'modifiedOriginals': {n: {'before': sha(original[n]), 'after': sha(result[n])} for n in changed},
        'newModules': {new: {'from': old, 'sha256': sha(result[new])} for old, new in sorted(mapping.items())},
        'moduleMapping': dict(sorted(mapping.items())), 'invariants': invariants, 'pricing': pricing,
        'sitemap': {'updatedUrls': list(SITEMAP_TARGETS), 'lastmod': publication_date, 'beforeSha256': sha(original['sitemap.xml']), 'afterSha256': sha(result['sitemap.xml'])},
        'nginx': {'beforeSha256': sha(nginx_before.encode()), 'afterSha256': sha(nginx.encode()), 'addedScriptHashes': added_hashes},
        'inventory': {n: sha(data) for n, data in sorted(result.items())},
    }
    return result, nginx, manifest


def build(pricing_path, output, release_id):
    output = Path(output)
    if output.exists() and any(output.iterdir()) and not (output/'release-manifest.json').is_file():
        raise ValueError('refusing non-release output directory')
    files, nginx, manifest = assemble_release(Path(pricing_path).read_text(), release_id)
    html = output/'html'; expected = set(files)
    if html.exists():
        actual = {str(p.relative_to(html)) for p in html.rglob('*') if p.is_file()}
        if actual-expected:
            raise ValueError('unexpected existing candidate files')
    for name, data in files.items():
        target = html/name
        if target.is_symlink(): raise ValueError('symlink output target')
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
    (output/'nginx').mkdir(parents=True, exist_ok=True)
    (output/'nginx/default.conf').write_text(nginx)
    (output/'release-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'candidate': str(output.resolve()), 'releaseId': release_id, 'files': len(files),
                      'newModules': len(manifest['newModules']), 'modifiedOriginals': list(manifest['modifiedOriginals']),
                      'newEntry': manifest['moduleMapping'][MAIN], 'newScriptHashes': len(manifest['nginx']['addedScriptHashes'])}, ensure_ascii=False))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pricing-html', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'artifacts/cn-search-content-20261027-release/candidate')
    parser.add_argument('--release-id', default='cn-search-content-20261027.1')
    args = parser.parse_args()
    build(args.pricing_html, args.output, args.release_id)
