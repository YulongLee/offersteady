import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import test from 'node:test';
import ts from 'typescript';
import {ROOT,makePatch,PAGE,CSS,VOICE,sha,parse} from './build_runtime_patch.mjs';
const baseline=resolve(ROOT,'artifacts/cn-mock-20261101-release/web-baseline');
const base=Object.fromEntries([PAGE,CSS].map(n=>[n,readFileSync(resolve(baseline,n),'utf8')]));
const handoff=JSON.parse(readFileSync(resolve(ROOT,'artifacts/cn-mock-server-local-20261031/combined-source-manifest.json')));
const func=(tree,name)=>tree.statements.find(n=>ts.isFunctionDeclaration(n)&&n.name?.text===name);

test('patch preserves all nonpage bytes and report/indicator implementations',()=>{
 const {modules,report}=makePatch(base,handoff),before=parse(base[PAGE]),after=parse(modules[PAGE]);
 const old=func(before,'ie').body,newBody=func(after,'ie').body;
 const importLine="import {MockVoicePlayer as __cnMockVoicePlayer,MockPlaybackError as __cnMockPlaybackError} from './cn-mock-voice-source.js';\n";
 const unpatched=modules[PAGE].replace(newBody.getText(after),old.getText(before)).slice(importLine.length);
 assert.equal(unpatched,base[PAGE]);
 for(const name of ['ae','re'])assert.equal(func(after,name).getText(after),func(before,name).getText(before));
 assert.equal(report.originalReportSha256,sha(func(before,'ae').getText(before)));
 assert.equal(report.runtimeBindings.mockRequest,'s');assert.equal(report.runtimeBindings.mockSocketUrl,'a');
 assert.equal(modules[CSS],base[CSS]+'\n'+report.cssAddedRules.join('\n')+'\n');
 assert.equal(report.cssAddedRules.length,3);assert.ok(!parse(modules[VOICE]).statements.some(ts.isImportDeclaration));
});
test('rejects frozen source handoff drift and scope expansion',()=>{
 const drift=structuredClone(handoff);drift.web['apps/web/src/MockInterviewPage.tsx']='0'.repeat(64);assert.throws(()=>makePatch(base,drift),/Frozen source drift/);
 const scope=structuredClone(handoff);scope.web.extra='0'.repeat(64);assert.throws(()=>makePatch(base,scope),/handoff scope/);
});
test('rejects active runtime import and export drift',()=>{
 assert.throws(()=>makePatch({...base,[PAGE]:base[PAGE].replace('S as a','S as changed')},handoff),/helper bridge/);
 assert.throws(()=>makePatch({...base,[PAGE]:base[PAGE].replace('ie as MockInterviewPage','ie as changed')},handoff),/mock exports/);
});
test('rejects prior CSS or missing selected AST declaration',()=>{
 assert.throws(()=>makePatch({...base,[CSS]:base[CSS]+'.mock-instructions{}'},handoff),/already exists/);
 assert.throws(()=>makePatch({...base,[PAGE]:base[PAGE].replace('function ie(','function changed(')},handoff),/Ambiguous ie/);
});
