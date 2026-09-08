import {spawn} from 'node:child_process';
import {mkdir, writeFile} from 'node:fs/promises';
import {join, resolve} from 'node:path';

const BASE = 'http://127.0.0.1:5200';
const OUT = resolve('out/qa/web');
const chromePath = process.env.CHROME_PATH ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
await mkdir(OUT, {recursive: true});

const browser = spawn(chromePath, [
  '--headless=new', '--disable-gpu', '--disable-background-media-suspend', '--disable-backgrounding-occluded-windows', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=0', '--autoplay-policy=no-user-gesture-required', '--user-data-dir=/tmp/offersteady-global-web-verification-chrome', `${BASE}/`,
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

await command('Runtime.enable');await command('Page.enable');await command('Page.bringToFront');
const results=[];
for(const [width,height,mobile] of [[1280,900,false],[390,844,true]]){
 await command('Emulation.setDeviceMetricsOverride',{width,height,mobile,deviceScaleFactor:1});
 await command('Page.navigate',{url:BASE});await command('Page.bringToFront');await pause(1200);
 await evaluate(`new Promise((resolve,reject)=>{const v=document.querySelector('video');if(v.readyState>=1)return resolve();v.onloadedmetadata=()=>resolve();v.onerror=()=>reject(new Error('video error'));})`);
 const playbackTime=await evaluate(`(async()=>{const v=document.querySelector('video');v.muted=true;v.currentTime=1;await v.play();await new Promise(resolve=>setTimeout(resolve,1200));return v.currentTime})()`);
 results.push(await evaluate(`(()=>{const v=document.querySelector('video');return{viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,duration:v.duration,videoWidth:v.videoWidth,videoHeight:v.videoHeight,playbackTime:${playbackTime},paused:v.paused,muted:v.muted,error:v.error?.message??null}})()`));
 await evaluate(`(()=>{const v=document.querySelector('video');v.pause();v.currentTime=20.4;})()`);await pause(1800);results.push(await evaluate(`(()=>{const v=document.querySelector('video');v.muted=false;const audioCanBeEnabled=!v.muted;v.muted=true;return {seekTime:v.currentTime,readyState:v.readyState,seeking:v.seeking,networkState:v.networkState,audioCanBeEnabled,decodedFrames:v.getVideoPlaybackQuality().totalVideoFrames,buffered:[...Array(v.buffered.length)].map((_,i)=>[v.buffered.start(i),v.buffered.end(i)])}})()`));await saveShot('preview-'+width);
}
await writeFile(join(OUT,'playback.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));
ws.close();stop();setTimeout(()=>process.exit(0),500);
