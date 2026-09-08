import {spawn} from 'node:child_process';
import {mkdir, writeFile} from 'node:fs/promises';
import {join, resolve} from 'node:path';

const BASE = process.env.OFFERSTEADY_GLOBAL_CAPTURE_BASE ?? 'http://127.0.0.1:5191';
const OUT = resolve('video/offersteady-device-story-global/public/textures');
const chromePath = process.env.CHROME_PATH ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
await mkdir(OUT, {recursive: true});

const browser = spawn(chromePath, [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=0', '--user-data-dir=/tmp/offersteady-device-story-global-chrome', `${BASE}/`,
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


const layout={};
async function take(name,path,w,h,action){
 await command('Emulation.setDeviceMetricsOverride',{width:w,height:h,deviceScaleFactor:2,mobile:false});
 await command('Page.navigate',{url:BASE+path});await pause(2200);await evaluate('document.fonts.ready');
 if(action){await evaluate(action);await pause(500)}
 if(path.includes('/live')){await evaluate(`Array.from(document.querySelectorAll('button')).find(x=>x.textContent.trim()==='Start Interview')?.click()`);await pause(800);}
 await evaluate(`(() => { const map=new Map([['This device · 正在收音','This device · Listening'],['正在收音','Listening']]); const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT); for(let node=walker.nextNode();node;node=walker.nextNode()){const value=map.get(node.textContent||'');if(value)node.textContent=value;} })()`);
 await saveShot(name);layout[name]={w,h,text:await evaluate('document.body.innerText')};
}
await take('desktop','/app/interviews/demo/live',1440,900);
await take('phone-answer','/app/interviews/demo/live',430,860);
await take('phone-question','/app/interviews/demo/live',430,860,`[...document.querySelectorAll('[role=tab]')].find(x=>x.textContent.includes('Conversation'))?.click()`);
await take('tablet','/app/interviews/demo/live',1024,768);
await writeFile(join(OUT,'layout.json'),JSON.stringify(layout,null,2));
ws.close();stop();
