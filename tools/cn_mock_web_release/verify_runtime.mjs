/** Execute existing mock regressions using functions from the assembled bytes.
 * Only the React/router host and download test seam are bridged for jsdom.
 * No whole application entry point is imported or mounted.
 */
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,dirname,basename} from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';
import {ROOT,sha,PAGE,VOICE} from './build_runtime_patch.mjs';

const [candidateArg,outputArg]=process.argv.slice(2);assert.ok(candidateArg&&outputArg,'Usage: verify_runtime.mjs candidate output');
const candidate=resolve(candidateArg),output=resolve(outputArg);mkdirSync(output,{recursive:true});
const manifest=JSON.parse(readFileSync(resolve(candidate,'web-manifest.json')));
const runtime=name=>resolve(candidate,'web/html',manifest.moduleMapping[name]??name);
for(const [name,sum]of Object.entries(manifest.inventory))assert.equal(sha(readFileSync(resolve(candidate,'web/html',name))),sum,`Candidate drift ${name}`);

function gatherModule(path) {
  const text=readFileSync(path,'utf8'),options={allowJs:true,noLib:true};
  const host=ts.createCompilerHost(options);
  host.getSourceFile=(name,version)=>name===path?ts.createSourceFile(name,text,version,true,ts.ScriptKind.JS):undefined;
  host.fileExists=name=>name===path;
  const program=ts.createProgram([path],options,host),tree=program.getSourceFile(path),checker=program.getTypeChecker();
  const top=new Map(),imported=new Map(),needed=new Set(),imports=new Map();
  for(const statement of tree.statements) {
    if(ts.isVariableStatement(statement))for(const declaration of statement.declarationList.declarations){
      function bind(name){
        if(ts.isIdentifier(name))top.set(checker.getSymbolAtLocation(name),declaration);
        else for(const element of name.elements)if(ts.isBindingElement(element))bind(element.name);
      }
      bind(declaration.name);
    }
    if((ts.isFunctionDeclaration(statement)||ts.isClassDeclaration(statement))&&statement.name)top.set(checker.getSymbolAtLocation(statement.name),statement);
    if(ts.isImportDeclaration(statement))for(const binding of statement.importClause?.namedBindings?.elements??[])imported.set(checker.getSymbolAtLocation(binding.name),{statement,binding});
  }
  function gather(node) {
    function visit(item) {
      if(ts.isIdentifier(item)) {
        const symbol=checker.getSymbolAtLocation(item);
        if(top.has(symbol)&&!needed.has(top.get(symbol))){needed.add(top.get(symbol));gather(top.get(symbol));}
        if(imported.has(symbol)){const {statement,binding}=imported.get(symbol);const values=imports.get(statement)??new Set();values.add(binding);imports.set(statement,values);}
      }
      ts.forEachChild(item,visit);
    }
    visit(node);
  }
  function exported(name) {
    const matches=tree.statements.filter(ts.isExportDeclaration).flatMap(s=>s.exportClause?.elements??[]).filter(e=>e.name.text===name);
    assert.equal(matches.length,1,`Export ${name}`);
    const binding=matches[0],symbol=checker.getSymbolAtLocation(binding.propertyName??binding.name),declaration=top.get(symbol);
    assert.ok(declaration,`Top declaration ${name}`);needed.add(declaration);gather(declaration);return declaration.name.text;
  }
  function render(replaceImport=path=>path) {
    return [...imports].map(([s,names])=>`import {${[...names].map(n=>n.getText(tree)).join(',')}} from ${JSON.stringify(replaceImport(resolve(dirname(path),s.moduleSpecifier.text)))};`).concat(
      [...needed].sort((a,b)=>a.pos-b.pos).map(n=>{
        const text=ts.isVariableDeclaration(n)?`const ${n.getText(tree)};`:n.getText(tree);
        return text.replace(/\bimport\((['"])(\.\/[^'"]+)\1\)/g,(_all,_quote,relative)=>`import(${JSON.stringify(resolve(dirname(path),relative))})`);
      })).join('\n');
  }
  return {tree,checker,top,needed,gather,exported,render};
}

const main=runtime('assets/main-559fbe0b.js'),auth=runtime('assets/auth-client-bd5688ab.js'),voice=runtime(VOICE);
const pureMain=gatherModule(main),request=pureMain.exported('x'),socket=pureMain.exported('S');
assert.match(pureMain.top.get(pureMain.checker.getSymbolAtLocation([...pureMain.tree.statements.filter(ts.isExportDeclaration).flatMap(s=>s.exportClause?.elements??[])].find(e=>e.name.text==='x').propertyName)).getText(pureMain.tree),/\.request\(/,'HTTP export contract');
assert.match(pureMain.top.get(pureMain.checker.getSymbolAtLocation([...pureMain.tree.statements.filter(ts.isExportDeclaration).flatMap(s=>s.exportClause?.elements??[])].find(e=>e.name.text==='S').propertyName)).getText(pureMain.tree),/\.protocol=/,'WebSocket URL export contract');
const transport=resolve(output,'actual-transports.mjs');
writeFileSync(transport,pureMain.render()+`\nexport {${request} as mockRequest,${socket} as mockSocketUrl};\n`);
const reactBridge=resolve(output,'react-host.mjs');
writeFileSync(reactBridge,`import * as React from 'react';import * as jsx from 'react/jsx-runtime';export const n=()=>React,t=()=>jsx;\n`);
const mainBridge=resolve(output,'mock-runtime-host.mjs');
writeFileSync(mainBridge,`export {Link as F,useNavigate as L,useParams as R} from 'react-router-dom';export {mockRequest as x,mockSocketUrl as S} from ${JSON.stringify(resolve(ROOT,'apps/web/src/mock-interview-client.ts'))};\n`);
const page=gatherModule(runtime(PAGE));
const pageName=page.exported('MockInterviewPage'),reportName=page.exported('MockReportView'),labels=page.exported('mockPhaseLabel');
const pageFixture=resolve(output,'actual-page.mjs');
writeFileSync(pageFixture,page.render(path=>path===main?mainBridge:basename(path)==='jsx-runtime-2Zwg-L3c.js'?reactBridge:path)+`\nexport {${pageName} as MockInterviewPage,${reportName} as MockReportView,${labels} as mockPhaseLabel};\n`);
// The old report's dynamic import stays byte-identical. Resolve only its test
// download boundary to the existing source mock used by the report regressions.
const word=runtime('assets/mock-interview-word-export-BOxeSAD1.js');
const clientFixture=resolve(output,'actual-client.mjs');
// Quote refresh is an unchanged original function; extract its exact initializer.
const quote=[...page.top.values()].find(n=>n.name?.text==='ne');assert.ok(quote);
writeFileSync(clientFixture,`export {MockVoicePlayer,MockPlaybackError} from ${JSON.stringify(voice)};export {mockRequest,mockSocketUrl} from ${JSON.stringify(transport)};\n${quote.getText(page.tree)}\nexport {ne as nextMockQuoteRefreshDelay};\n`);
const authFixture=resolve(output,'actual-auth.mjs');writeFileSync(authFixture,`export {t as authClient} from ${JSON.stringify(auth)};\n`);
const transportTest=resolve(output,'actual-transport.test.ts');
writeFileSync(transportTest,`import {expect,it,vi,afterEach} from 'vitest';
import {mockRequest,mockSocketUrl} from ${JSON.stringify(transport)};
import {MockVoicePlayer,MockPlaybackError} from ${JSON.stringify(voice)};
import {t as authClient} from ${JSON.stringify(auth)};
import {mockRequest as importedRequest,MockVoicePlayer as importedPlayer,MockPlaybackError as importedError} from ${JSON.stringify(resolve(ROOT,'apps/web/src/mock-interview-client.ts'))};
afterEach(()=>{vi.unstubAllGlobals();vi.restoreAllMocks();});
it('uses actual HTTP export x with original auth, JSON body and error propagation',async()=>{
 vi.spyOn(authClient,'readStoredSession').mockReturnValue({accessToken:'synthetic-token',account:{id:'synthetic'}} as any);
 const fetch=vi.fn(async()=>new Response(JSON.stringify({synthetic:true}),{status:200,headers:{'Content-Type':'application/json'}}));vi.stubGlobal('fetch',fetch);
 expect(await mockRequest('/mock-interviews/synthetic',{synthetic:true})).toEqual({synthetic:true});
 expect(fetch).toHaveBeenCalledOnce();const [url,init]=fetch.mock.calls[0] as any;
 expect(url).toBe('/api/v1/mock-interviews/synthetic');expect(init.method).toBe('POST');expect(init.credentials).toBeUndefined();expect(init.signal).toBeNull();
 const headers=new Headers(init.headers);expect(headers.get('Authorization')).toBe('Bearer synthetic-token');expect(headers.get('Content-Type')).toBe('application/json');expect(JSON.parse(init.body)).toEqual({synthetic:true});
 fetch.mockResolvedValueOnce(new Response(JSON.stringify({synthetic:'conflict'}),{status:409,headers:{'Content-Type':'application/json'}}));
 await expect(mockRequest('/mock-interviews/synthetic')).rejects.toMatchObject({status:409,payload:{synthetic:'conflict'}});expect(fetch).toHaveBeenCalledTimes(2);
});
it('uses actual WS export S and keeps one player/error class identity',()=>{
 const expected=new URL('/api/v1/mock-interviews/synthetic%20%2F/control',window.location.origin);expected.protocol=expected.protocol==='https:'?'wss:':'ws:';
 expect(mockSocketUrl('synthetic /')).toBe(expected.toString());expect(importedRequest).toBe(mockRequest);expect(importedPlayer).toBe(MockVoicePlayer);expect(importedError).toBe(MockPlaybackError);
});\n`);
for(const name of [transport,pageFixture,clientFixture,authFixture,reactBridge,mainBridge]){
  const checked=spawnSync('node',['--check',name],{encoding:'utf8'});assert.equal(checked.status,0,checked.stderr);
}
const replacements={
  [resolve(ROOT,'apps/web/src/MockInterviewPage.tsx')]:pageFixture,
  [resolve(ROOT,'apps/web/src/mock-interview-client.ts')]:clientFixture,
  [resolve(ROOT,'apps/web/src/auth-client.ts')]:authFixture,
};
const config=resolve(output,'vitest.config.mjs');
writeFileSync(config,`import {defineConfig} from 'vitest/config';import {readFileSync} from 'node:fs';
const replacements=${JSON.stringify(replacements)};
export default defineConfig({root:${JSON.stringify(ROOT)},resolve:{alias:[{find:${JSON.stringify(word)},replacement:${JSON.stringify(resolve(ROOT,'apps/web/src/mock-interview-word-export.ts'))}}]},plugins:[{name:'actual-mock-release-substitution',enforce:'pre',load(id){const file=id.split('?')[0];if(replacements[file])return readFileSync(replacements[file],'utf8');}}],test:{environment:'jsdom',setupFiles:[${JSON.stringify(resolve(ROOT,'apps/web/src/test/setup.ts'))}],maxWorkers:2}});`);
const files=['apps/web/src/MockInterviewPage.test.tsx','apps/web/src/mock-interview-client.test.ts','apps/web/src/MockInterviewPage.playback-recovery.test.tsx',transportTest];
const run=spawnSync(resolve(ROOT,'node_modules/.bin/vitest'),['run','--config',config,...files,'--reporter=default','--reporter=junit',`--outputFile.junit=${resolve(output,'actual-mock-junit.xml')}`],{cwd:ROOT,encoding:'utf8',timeout:120000,env:{...process.env,HTTP_PROXY:'',HTTPS_PROXY:'',ALL_PROXY:'',NO_PROXY:'*'}});
writeFileSync(resolve(output,'actual-mock-tests.txt'),run.stdout+run.stderr);console.log(run.stdout);if(run.stderr)console.error(run.stderr);
assert.equal(run.status,0,'Assembled mock function regressions failed');
const junit=readFileSync(resolve(output,'actual-mock-junit.xml'),'utf8'),tests=Number(junit.match(/<testsuites\b[^>]*\btests="(\d+)"/)?.[1]);assert.ok(tests>=56);
writeFileSync(resolve(output,'actual-mock-verification.json'),JSON.stringify({passed:true,tests,manifestSha256:sha(readFileSync(resolve(candidate,'web-manifest.json'))),actualPageBodyAndReportExtracted:true,actualNewPlayerImported:true,actualOriginalTransportsExtracted:true,actualTransportDirectSyntheticFetchAndWsUrlPassed:true,sharedPlayerAndErrorClassIdentityPassed:true,originalAuthAndJsonClientImported:true,pageTransportMockedByExistingUnitTests:true,reactAndRouterHostBridgedForJsdom:true,downloadBoundaryUsesExistingTestMock:true,noApplicationBootstrapImported:true,noProductionOrModelCalls:true,testFiles:files},null,2)+'\n');
