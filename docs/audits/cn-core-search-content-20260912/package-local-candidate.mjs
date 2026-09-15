import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';

const root = process.cwd();
const base = path.join(root, 'artifacts/cn-homepage-layout.82qdGV');
const candidate = path.join(base, 'candidate');
const before = path.join(base, 'seo-round1-before');
const out = path.join(base, 'seo-round1-validation');
fs.mkdirSync(out, { recursive: true });
const production = [
  'apps/web/public/seo/realtime-interview.html',
  'apps/web/public/seo/ai-interview-assistant.html',
  'apps/web/public/seo/pricing.html',
  'apps/web/public/seo/download.html',
  'apps/web/public/seo/public-search.css',
  'apps/web/public/llms.txt', 'apps/web/public/llms-full.txt', 'apps/web/public/public-facts.json',
  'apps/web/public/sitemap.xml', 'infra/nginx/default.conf',
  'apps/web/core-search-content.test.ts', 'apps/web/scripts/verify-seo-p0.mjs',
];
const preview = ['apps/web/vite.layout-preview.config.ts', 'apps/web/src/test/layout-preview.tsx'];
function bundle(name, files) {
  const chunks = [];
  for (const file of files) {
    const oldPath = fs.existsSync(path.join(before, file)) ? path.join(before, file) : '/dev/null';
    const newPath = path.join(candidate, file);
    const diff = spawnSync('git', ['diff', '--no-index', '--no-prefix', '--', oldPath, newPath], { encoding: 'utf8', maxBuffer: 8 * 1024 * 1024 });
    if (diff.status !== 1) throw new Error(`Expected changed file ${file}: ${diff.stderr}`);
    chunks.push(diff.stdout.replace(/^diff --git .*$/m, `diff --git a/${file} b/${file}`)
      .replace(/^--- .*$/m, oldPath === '/dev/null' ? '--- /dev/null' : `--- a/${file}`)
      .replace(/^\+\+\+ .*$/m, `+++ b/${file}`));
  }
  fs.writeFileSync(path.join(out, `${name}.patch`), chunks.join(''));
  const tar = spawnSync('tar', ['-czf', path.join(out, `${name}-overlay.tgz`), '-C', candidate, ...files], { encoding: 'utf8' });
  if (tar.status !== 0) throw new Error(tar.stderr);
  return files.map(file => ({ file, bytes: fs.statSync(path.join(candidate, file)).size, sha256: createHash('sha256').update(fs.readFileSync(path.join(candidate, file))).digest('hex') }));
}
const manifest = {
  version: 'cn-search-content-20260912.local', createdAt: new Date().toISOString(), deployed: false,
  parentCandidate: 'cn-homepage-refined-20260912.local',
  note: 'Incremental only. Apply after the reviewed round3 candidate, not the dirty root workspace. Rebuild and verify live pricing before any future deployment.',
  production: bundle('source', production), previewOnly: bundle('preview-support', preview),
};
fs.writeFileSync(path.join(out, 'patch-manifest.json'), JSON.stringify(manifest, null, 2));
const latest = JSON.parse(fs.readFileSync(path.join(candidate, 'candidate-tests-seo-round1.json'), 'utf8'));
const prior = JSON.parse(fs.readFileSync(path.join(base, 'candidate-tests-round3.json'), 'utf8'));
const failures = d => d.testResults.flatMap(t => t.assertionResults.filter(a => a.status === 'failed').map(a => a.fullName));
const result = { total: latest.numTotalTests, passed: latest.numPassedTests, failed: latest.numFailedTests, failures: failures(latest), newFailures: failures(latest).filter(n => !failures(prior).includes(n)) };
fs.writeFileSync(path.join(out, 'test-comparison.json'), JSON.stringify(result, null, 2));
const persistent = path.join(root, 'design/previews/cn-homepage-layout/seo-round1');
fs.mkdirSync(persistent, { recursive: true });
for (const file of ['source.patch', 'source-overlay.tgz', 'preview-support.patch', 'preview-support-overlay.tgz', 'patch-manifest.json', 'test-comparison.json']) {
  fs.copyFileSync(path.join(out, file), path.join(persistent, file));
}
console.log(JSON.stringify({ version: manifest.version, productionFiles: production.length, previewOnlyFiles: preview.length, tests: result }, null, 2));
