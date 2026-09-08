import {spawn} from 'node:child_process';
import {mkdir, writeFile} from 'node:fs/promises';
import {join, resolve} from 'node:path';

const BASE = process.env.OFFERSTEADY_GLOBAL_CAPTURE_BASE ?? 'http://127.0.0.1:5188';
const OUT = resolve('video/offersteady-global-commercial/public/textures');
const chromePath = process.env.CHROME_PATH ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
await mkdir(OUT, {recursive: true});

const browser = spawn(chromePath, [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=0', '--user-data-dir=/tmp/offersteady-global-commercial-chrome', `${BASE}/`,
], {stdio: ['ignore', 'ignore', 'pipe']});
const stop = () => { if (!browser.killed) browser.kill('SIGTERM'); };
process.once('exit', stop);

const devtoolsUrl = await new Promise((resolveUrl, reject) => {
  const timer = setTimeout(() => reject(new Error('Chrome DevTools startup timed out')), 10000);
  browser.stderr.setEncoding('utf8');
  browser.stderr.on('data', chunk => {
    const match = chunk.match(/DevTools listening on (ws:\/\/[^\s]+)/);
    if (match) { clearTimeout(timer); resolveUrl(match[1]); }
  });
});
const ws = new WebSocket(devtoolsUrl);
await new Promise((ok, fail) => { ws.onopen = ok; ws.onerror = fail; });
let sequence = 0;
const pending = new Map();
ws.onmessage = event => {
  const message = JSON.parse(event.data);
  if (!message.id || !pending.has(message.id)) return;
  const entry = pending.get(message.id); pending.delete(message.id);
  message.error ? entry.reject(new Error(message.error.message)) : entry.resolve(message.result);
};
const rootCommand = (method, params = {}) => new Promise((resolveCommand, reject) => {
  const id = ++sequence; pending.set(id, {resolve: resolveCommand, reject}); ws.send(JSON.stringify({id, method, params}));
});
const {targetInfos} = await rootCommand('Target.getTargets');
const target = targetInfos.find(item => item.type === 'page');
const {sessionId} = await rootCommand('Target.attachToTarget', {targetId: target.targetId, flatten: true});
const command = (method, params = {}) => new Promise((resolveCommand, reject) => {
  const id = ++sequence; pending.set(id, {resolve: resolveCommand, reject}); ws.send(JSON.stringify({id, sessionId, method, params}));
});
const pause = ms => new Promise(ok => setTimeout(ok, ms));
const evaluate = async expression => {
  const result = await command('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true});
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description ?? result.exceptionDetails.text);
  return result.result.value;
};
const saveShot = async (name, clip, captureBeyondViewport = false) => {
  const shot = await command('Page.captureScreenshot', {format: 'png', fromSurface: true, captureBeyondViewport, ...(clip ? {clip} : {})});
  await writeFile(join(OUT, `${name}.png`), Buffer.from(shot.data, 'base64'));
};
const bbox = selector => evaluate(`(() => { const el=document.querySelector(${JSON.stringify(selector)}); if(!el)return null; const r=el.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; })()`);

await command('Runtime.enable');
await command('Page.enable');
await command('Network.enable');
await command('Network.setBlockedURLs', {urls:['https://*','http://127.0.0.1:8000/*','http://127.0.0.1:9/*']});
await command('Emulation.setDeviceMetricsOverride', {width: 1920, height: 1080, deviceScaleFactor: 2, mobile: false});
await command('Page.navigate', {url: `${BASE}/`});
await pause(700);
await evaluate(`localStorage.setItem('offersteady.prototype.auth','true')`);

const pages = [
  {name: 'landing', path: '/', selectors: ['.landing-hero', '.answer-demo']},
  {name: 'live', path: '/app/interviews/demo/live', selectors: ['.live-top', '.conversation-monitor', '.answer-workspace', '.answer-action-bar', '.simple-answer', '.detailed-answer', '.advice-footer', '.transcript-list', '.transcript-turns', '.advice-card', '.current-question', '.conversation-lines']},
  {name: 'screenshot', path: '/app/interviews/demo/live?capture=screenshot', selectors: ['.answer-workspace','.simple-answer','.detailed-answer','.answer-action-bar']},
  {name: 'prepare', path: '/app/interviews/demo/prepare', selectors: ['.resource-card', '.context-selection', '.preparation-materials']},
  {name: 'review', path: '/app/interviews/demo/review', selectors: ['.review-main', '.review-summary', '.review-timeline']},
  {name: 'library', path: '/app/library', selectors: ['.app-page', '.library-list', '.material-section']},
];
const layout = {};
for (const page of pages) {
  await command('Page.navigate', {url: `${BASE}${page.path}`});
  await pause(page.name === 'live' ? 1900 : 1000);
  await evaluate(`document.fonts.ready`);
  await pause(650);
  await evaluate(`(() => {
    const replacements = new Map([
      ['This device · 已连接，未采集', 'This device · Connected · Not capturing'],
      ['已连接，未采集', 'Connected · Not capturing'],
      ['42 分钟', '42 minutes']
    ]);
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const replacement = replacements.get(node.textContent || '');
      if (replacement) node.textContent = replacement;
    }
  })()`);
  await saveShot(`${page.name}-full`);
  await writeFile(join(OUT, `${page.name}-dom.json`), JSON.stringify(await evaluate(`({text:document.body.innerText,classes:[...new Set([...document.querySelectorAll('[class]')].map(e=>e.className).filter(x=>typeof x==='string'))]})`),null,2));
  layout[page.name] = {pageH: await evaluate('document.documentElement.scrollHeight'), elements: {}};
  for (const selector of page.selectors) {
    const rect = await bbox(selector);
    if (!rect || rect.w < 1 || rect.h < 1) continue;
    const key = selector.replace(/^[.#]/, '').replace(/[^a-z0-9_-]+/gi, '-');
    layout[page.name].elements[key] = rect;
    await saveShot(`${page.name}-${key}`, {x: rect.x, y: rect.y, width: rect.w, height: rect.h, scale: 2});
  }

  if (page.name === 'live' || page.name === 'screenshot') {
    const rect = await bbox('.answer-workspace');
    await evaluate(`document.querySelectorAll('.simple-answer,.detailed-answer,.advice-footer').forEach(e=>e.style.visibility='hidden')`);
    await saveShot(page.name+'-answer-empty', {x:rect.x,y:rect.y,width:rect.w,height:rect.h,scale:2});
    await evaluate(`document.querySelectorAll('.simple-answer,.detailed-answer,.advice-footer').forEach(e=>e.style.visibility='')`);
    const rows = await evaluate(`Array.from(document.querySelectorAll('.detailed-answer .answer-markdown > *')).map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,text:e.textContent}})`);
    layout[page.name].answerRows = rows;
    for(let i=0;i<rows.length;i++){ const r=rows[i];await saveShot(page.name+'-answer-row-'+i,{x:r.x,y:r.y,width:r.w,height:r.h,scale:2}); }
  }
  if (page.name === 'library') {
    for (const [i,label] of ['Resume','Job Description','Knowledge'].entries()) {
      await evaluate(`Array.from(document.querySelectorAll('.material-tabs button')).find(e=>e.textContent.includes(${JSON.stringify(label)}))?.click()`);
      await pause(600);
      const sel = '.document-list article, .typed-material-list article';
      const r = await bbox(sel);
      layout.library.elements['material-'+i] = r;
      if(r) await saveShot('material-'+i,{x:r.x,y:r.y,width:r.w,height:r.h,scale:2});
      await writeFile(join(OUT,'library-'+i+'-dom.json'),JSON.stringify(await evaluate(`({text:document.body.innerText,classes:[...new Set([...document.querySelectorAll('[class]')].map(e=>e.className).filter(x=>typeof x==='string'))]})`),null,2));
    }
  }
  if (false) {
    await evaluate(`(() => {
      const pricing = document.querySelector('#pricing-value');
      if (!pricing) return false;
      pricing.querySelectorAll('article strong').forEach(node => { node.textContent = '成本价使用'; });
      pricing.querySelectorAll('article p').forEach((node, index) => {
        node.textContent = index === 0 ? '偶尔使用按次选择，按实际成功结果结算。' : '面试密集期按天选择，时间安排更灵活。';
      });
      pricing.scrollIntoView({block: 'center'});
      return true;
    })()`);
    await pause(700);
    await saveShot('landing-pricing-full');
    const rect = await evaluate(`(() => {
      const el = document.querySelector('#pricing-value');
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return {x: r.x + window.scrollX, y: r.y + window.scrollY, w: r.width, h: r.height};
    })()`);
    if (rect) {
      layout.landing.elements['pricing-value'] = rect;
      await saveShot('landing-pricing-value', {x: rect.x, y: rect.y, width: rect.w, height: rect.h, scale: 2}, true);
    }
  }
}

await writeFile(join(OUT, 'layout.json'), JSON.stringify(layout, null, 2));
ws.close(); stop();
process.stdout.write(`${JSON.stringify({out: OUT, pages: Object.keys(layout)}, null, 2)}\n`);
