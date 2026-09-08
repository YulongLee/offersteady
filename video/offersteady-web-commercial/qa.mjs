import {bundle} from '@remotion/bundler';
import {selectComposition,renderStill,openBrowser} from '@remotion/renderer';
import {resolve} from 'node:path';
import {mkdir} from 'node:fs/promises';
const serveUrl=await bundle({entryPoint:resolve('src/index.ts'),publicDir:resolve('public')});
const browserExecutable='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const puppeteerInstance=await openBrowser('chrome',{browserExecutable,chromiumOptions:{gl:'angle'}});
const composition=await selectComposition({serveUrl,id:'OfferSteadyCommercial',puppeteerInstance});
await mkdir('out/qa',{recursive:true});
const frames=process.argv.slice(2).map(Number);
for (const frame of frames.length?frames:[90,210,330,500,660,850,1020,1240,1450,1680,1880,2100]) {
 await renderStill({serveUrl,composition,frame,output:`out/qa/f${frame}.png`,puppeteerInstance,imageFormat:'png'});
 console.log(`QA ${frame}`);
}
await puppeteerInstance.close({silent:true});
