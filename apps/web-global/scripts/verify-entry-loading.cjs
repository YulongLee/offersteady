// Read-only local browser QA. All APIs are intercepted with synthetic data.
// NODE_PATH can point to the bundled Codex Playwright runtime.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
const base = process.env.GLOBAL_ENTRY_PREVIEW_URL || 'http://127.0.0.1:4297';
const output = path.resolve(root, '../..', 'artifacts/global-entry-loading-20260929');
const envelope = data => ({ success: true, data, error: null, requestId: 'synthetic-entry-qa', meta: { apiVersion: 'v1', timestamp: 'synthetic' } });

function entryGraph(dist) {
  const html = fs.readFileSync(path.join(dist, 'index.html'), 'utf8');
  const entries = [...html.matchAll(/<script[^>]*type="module"[^>]*src="([^"]+)"/g)].map(match => match[1].replace(/^\//, ''));
  const seen = new Set();
  const manifestPath = path.join(dist, '.vite/manifest.json');
  const manifest = fs.existsSync(manifestPath) ? JSON.parse(fs.readFileSync(manifestPath, 'utf8')) : {};
  const walk = file => {
    if (seen.has(file)) return;
    seen.add(file);
    const item = Object.values(manifest).find(item => item.file === file);
    for (const key of item?.imports || []) walk(manifest[key].file);
  };
  entries.forEach(walk);
  const scripts = [...seen].filter(file => file.endsWith('.js'));
  return { scripts, rawBytes: scripts.reduce((sum, file) => sum + fs.statSync(path.join(dist, file)).size, 0), gzipBytes: scripts.reduce((sum, file) => sum + zlib.gzipSync(fs.readFileSync(path.join(dist, file))).length, 0) };
}

(async () => {
  fs.mkdirSync(output, { recursive: true });
  const candidate = entryGraph(path.join(root, 'dist'));
  const baseline = entryGraph(path.resolve(root, '../..', 'artifacts/global-practice-20260929/candidate/apps/web-global/dist'));
  assert(candidate.gzipBytes < baseline.gzipBytes * 0.8, 'public entry should shrink by at least 20% at identical gzip settings');
  assert(candidate.scripts.every(file => !/WorkspaceApp|AnswerWorkspace|MockInterview|LibraryManager/.test(file)));
  for (const file of candidate.scripts) assert(!fs.readFileSync(path.join(root, 'dist', file), 'utf8').includes('/api/v1/web/state'), 'business-state client must be outside public entry');
  const { syntheticState } = await import(pathToFileURL(path.resolve(root, '../web/src/test-state.ts')));
  const synthetic = structuredClone(syntheticState);
  synthetic.account = { id: 'synthetic-browser-user', displayName: 'Synthetic candidate', createdAtMs: 1, bindings: [] };
  synthetic.interviews = [];
  const user = { userId: synthetic.account.id, displayName: synthetic.account.displayName, createdAtMs: 1, bindings: [] };
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  const checks = [];
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const page = await context.newPage();
    const requests = [];
    let mode = 'blocked';
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => requests.push(new URL(request.url()).pathname));
    await context.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.origin !== new URL(base).origin) return route.abort();
      if (!url.pathname.startsWith('/api/')) return route.continue();
      if (mode === 'blocked') return route.fulfill({ status: 503, contentType: 'application/json', body: '{}' });
      let data;
      if (url.pathname.endsWith('/auth/global/password/login')) data = { user, tokens: { accessToken: 'synthetic-access', refreshToken: 'synthetic-refresh' } };
      else if (url.pathname.endsWith('/auth/me')) data = user;
      else if (url.pathname.endsWith('/web/state')) data = synthetic;
      else if (url.pathname.endsWith('/promotion/claim')) data = { accepted: true };
      else if (url.pathname.endsWith('/auth/logout')) data = { loggedOut: true };
      else return route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(envelope(data)) });
    });

    await page.goto(base + '/', { waitUntil: 'networkidle' });
    await page.locator('.commercial-home').waitFor();
    assert(!requests.some(url => url.startsWith('/api/')), 'public homepage requested API');
    assert(!requests.some(url => url.startsWith('/media/')), 'offscreen media was fetched');
    assert(!requests.some(url => /WorkspaceApp|product-edition-/.test(url)), 'workspace dependency loaded at homepage');
    await page.screenshot({ path: path.join(output, 'home-desktop.png'), fullPage: false });
    checks.push('homepage renders with unavailable API; no business API/workspace/media requests');
    await page.getByRole('button', { name: 'Play OfferSteady product film', exact: true }).scrollIntoViewIfNeeded();
    await page.waitForFunction(() => document.querySelector('video[aria-label="OfferSteady product film"]')?.getAttribute('poster'));
    assert(!requests.some(url => url.endsWith('.mp4')), 'video fetched before click');
    const mediaRequest = page.waitForRequest(request => request.url().endsWith('offersteady-global-commercial-20260907.mp4'));
    await page.getByRole('button', { name: 'Play OfferSteady product film', exact: true }).click();
    await mediaRequest;
    await page.waitForFunction(() => { const video = document.querySelector('video[aria-label="OfferSteady product film"]'); return video && video.readyState >= 2 && !video.paused; });
    checks.push('poster visible near viewport; MP4 requested and plays only after click');

    requests.length = 0;
    await page.goto(base + '/login', { waitUntil: 'networkidle' });
    await page.getByLabel('Email address').waitFor();
    assert(!requests.some(url => url.startsWith('/api/') || /WorkspaceApp/.test(url)));
    await page.screenshot({ path: path.join(output, 'login-desktop.png') });
    checks.push('login form works with backend unavailable and without workspace chunk');

    requests.length = 0;
    await page.goto(base + '/app/settings?from=entry-qa#preferences', { waitUntil: 'networkidle' });
    assert(new URL(page.url()).pathname === '/login');
    assert(!requests.some(url => /web\/state|WorkspaceApp/.test(url)));
    mode = 'authenticated';
    await page.getByLabel('Email address').fill('synthetic@example.com');
    await page.getByLabel('Password', { exact: true }).fill('synthetic password for local QA');
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await page.getByRole('heading', { name: 'Settings', exact: true }).waitFor();
    assert(page.url().endsWith('/app/settings?from=entry-qa#preferences'));
    const stateCount = requests.filter(url => url === '/api/v1/web/state').length;
    assert.equal(stateCount, 1);
    await page.getByRole('navigation', { name: 'Application navigation', exact: true }).getByRole('link', { name: 'Interviews', exact: true }).click();
    await page.getByRole('heading', { name: 'Your interviews', exact: true }).waitFor();
    assert.equal(requests.filter(url => url === '/api/v1/web/state').length, 1, 'workspace remounted on navigation');
    await page.screenshot({ path: path.join(output, 'workspace-desktop.png') });
    await page.getByRole('button', { name: 'Account menu', exact: true }).first().click();
    await page.getByRole('button', { name: 'Sign out', exact: true }).first().click();
    await page.getByLabel('Password', { exact: true }).waitFor();
    assert(!await page.evaluate(() => localStorage.getItem('offersteady.auth.access_token')));
    checks.push('protected deep link, password login, validated state, internal navigation and logout');

    mode = 'blocked';
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(base + '/', { waitUntil: 'networkidle' });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'mobile overflow');
    await page.screenshot({ path: path.join(output, 'home-mobile.png') });
    await page.goto(base + '/login', { waitUntil: 'networkidle' });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'login mobile overflow');
    await page.screenshot({ path: path.join(output, 'login-mobile.png') });
    checks.push('390px responsive homepage/login without horizontal overflow');
    assert.deepEqual(errors, []);
    const report = { baselineVersion: '20260929-global-practice-1', baseline, candidate, gzipReductionPercent: +(100 * (1 - candidate.gzipBytes / baseline.gzipBytes)).toFixed(1), checks, errors, note: 'Local built-page checks with synthetic APIs, not production latency or real payment/audio acceptance.' };
    fs.writeFileSync(path.join(output, 'verification.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
