/** Run the existing state-read regressions against functions extracted from the
 * actual assembled modules, without mounting a page or contacting a provider.
 */
import assert from "node:assert/strict";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import ts from "typescript";

const ROOT=resolve(fileURLToPath(new URL("../..",import.meta.url)));
const [candidateArg,outputArg]=process.argv.slice(2);
assert.ok(candidateArg&&outputArg,"Usage: verify_web_runtime_package.mjs <candidate-root> <output-dir>");
const candidate=resolve(candidateArg), output=resolve(outputArg);
mkdirSync(output,{recursive:true});
const manifest=JSON.parse(readFileSync(resolve(candidate,"web-manifest.json"),"utf8"));
const html=resolve(candidate,"web/html");
for(const name of Object.keys(manifest.newModules)){
  const r=spawnSync("node",["--check","--input-type=module"],{input:readFileSync(resolve(html,name)),encoding:"utf8"});
  assert.equal(r.status,0,`${name}: ${r.stderr}`);
}
const runtimeFile = from => resolve(html,manifest.moduleMapping[from]);

function parseRuntime(path){
  const text=readFileSync(path,"utf8");
  const host=ts.createCompilerHost({allowJs:true,noLib:true});
  host.getSourceFile=(f,v)=>f===path?ts.createSourceFile(f,text,v,true,ts.ScriptKind.JS):undefined;
  host.fileExists=f=>f===path;
  const program=ts.createProgram([path],{allowJs:true,noLib:true},host);
  const tree=program.getSourceFile(path), checker=program.getTypeChecker(), top=new Map(), imported=new Map();
  for(const statement of tree.statements){
    if(ts.isVariableStatement(statement))for(const d of statement.declarationList.declarations)if(ts.isIdentifier(d.name))top.set(checker.getSymbolAtLocation(d.name),d);
    if(ts.isFunctionDeclaration(statement)||ts.isClassDeclaration(statement))if(statement.name)top.set(checker.getSymbolAtLocation(statement.name),statement);
    if(ts.isImportDeclaration(statement))for(const binding of statement.importClause?.namedBindings?.elements??[])imported.set(checker.getSymbolAtLocation(binding.name),{statement,binding});
  }
  const needed=new Set(), importBindings=new Map();
  function gather(node){
    function visit(n){
      if(ts.isIdentifier(n)){
        const symbol=checker.getSymbolAtLocation(n);
        if(top.has(symbol)&&!needed.has(top.get(symbol))){const declaration=top.get(symbol);needed.add(declaration);gather(declaration);}
        if(imported.has(symbol)){const {statement,binding}=imported.get(symbol);const entry=importBindings.get(statement)??new Set();entry.add(binding);importBindings.set(statement,entry);}
      }
      ts.forEachChild(n,visit);
    }
    visit(node);
  }
  return {tree,checker,top,needed,gather,render(){
    const imports=[...importBindings].map(([s,bindings])=>`import {${[...bindings].map(b=>b.getText(tree)).join(",")}} from ${JSON.stringify(resolve(dirname(path),s.moduleSpecifier.text))};`);
    const declarations=[...needed].sort((a,b)=>a.pos-b.pos).map(n=>ts.isVariableDeclaration(n)?`const ${n.getText(tree)};`:n.getText(tree));
    return [...imports,...declarations].join("\n");
  }};
}
const m=parseRuntime(runtimeFile("assets/main-0d73b38b.js"));
const mainClasses=[];
function visit(n){if(ts.isClassExpression(n)&&n.members.some(m=>m.name?.getText()==="loadState"))mainClasses.push(n);ts.forEachChild(n,visit)}visit(m.tree);
assert.equal(mainClasses.length,1);
const members=mainClasses[0].members.filter(n=>ts.isConstructorDeclaration(n)||["loadState","submitManualAnswer","submitManualAnswerStream"].includes(n.name?.getText(m.tree)));
assert.equal(members.length,4);
for(const node of members)m.gather(node);
const refresh=[...m.top.values()].find(n=>n.name?.getText(m.tree)==="di");assert.ok(refresh);m.needed.add(refresh);m.gather(refresh);
const methodsPath=runtimeFile("assets/cn-state-read-methods-source.js");
const authPath=runtimeFile("assets/auth-client-CpBLJDBI.js");
const statePath=runtimeFile("assets/cn-state-read-scope-source.js");
const adapterFixture=resolve(output,"actual-adapter.mjs");
writeFileSync(adapterFixture,`${m.render()}
import {installStateReadOptimization} from ${JSON.stringify(methodsPath)};
const ActualAdapter=class {${members.map(n=>n.getText(m.tree)).join("\n")}};
export class BackendPreviewInterviewAdapter extends ActualAdapter {constructor(...args){super(...args);installStateReadOptimization(this,d,N);}}
export const createAuthRefreshingFetch=di;
`);
const r=parseRuntime(runtimeFile("assets/ResumeOptimizerPage-131170b3.js"));
const clients=[];function findClient(n){if((ts.isClassDeclaration(n)||ts.isClassExpression(n))&&n.members.some(m=>m.name?.getText(r.tree)==="response"&&m.getText(r.tree).includes("无法连接简历优化服务")))clients.push(n);ts.forEachChild(n,findClient)}findClient(r.tree);
assert.equal(clients.length,1);
for(const n of clients[0].members)r.gather(n);
// Gathering the class name itself would pull its declaration twice.
const client=clients[0], classText=client.getText(r.tree).replace(/^class\s+[A-Za-z_$][\w$]*/,"class");
const resumeFixture=resolve(output,"actual-resume-client.mjs");
writeFileSync(resumeFixture,`${r.render()}\nexport const BackendResumeOptimizerClient=${classText};\n`);
for(const name of [adapterFixture,resumeFixture]){const result=spawnSync("node",["--check",name],{encoding:"utf8"});assert.equal(result.status,0,result.stderr);}

const apiFixture=resolve(output,"actual-api.mjs"),authFixture=resolve(output,"actual-auth.mjs"),stateFixture=resolve(output,"actual-state.mjs");
writeFileSync(apiFixture,`export {r as createJsonClient,a as withBaseUrl,i as runAdapterOperation} from ${JSON.stringify(authPath)};\n`);
writeFileSync(authFixture,`export {t as authClient} from ${JSON.stringify(authPath)};\n`);
writeFileSync(stateFixture,`export * from ${JSON.stringify(statePath)};\n`);
const replacements={
  [resolve(ROOT,"apps/web/src/backend-adapter.ts")]:adapterFixture,
  [resolve(ROOT,"apps/web/src/auth-client.ts")]:authFixture,
  [resolve(ROOT,"apps/web/src/api-client.ts")]:apiFixture,
  [resolve(ROOT,"apps/web/src/state-read-scope.ts")]:stateFixture,
  [resolve(ROOT,"apps/web/src/resume-optimizer-client.ts")]:resumeFixture,
};
const config=resolve(output,"vitest.config.mjs");
writeFileSync(config,`import {defineConfig} from 'vitest/config';
import {readFileSync} from 'node:fs';
const replacements=${JSON.stringify(replacements)};
export default defineConfig({root:${JSON.stringify(ROOT)},plugins:[{name:'actual-release-module-substitution',enforce:'pre',load(id){const path=id.split('?')[0];if(replacements[path])return readFileSync(replacements[path],'utf8');}}],test:{environment:'jsdom',setupFiles:[${JSON.stringify(resolve(ROOT,"apps/web/src/test/setup.ts"))}],maxWorkers:2}});`);
const testFiles=["apps/web/src/backend-adapter-state.test.ts","apps/web/src/backend-adapter-state-stream.test.ts","apps/web/src/state-read-scope.test.ts"];
const result=spawnSync(resolve(ROOT,"node_modules/.bin/vitest"),["run","--config",config,...testFiles,"--reporter=default","--reporter=junit",`--outputFile.junit=${resolve(output,"actual-runtime-junit.xml")}`],{cwd:ROOT,encoding:"utf8",timeout:120000,env:{...process.env,HTTP_PROXY:"",HTTPS_PROXY:"",ALL_PROXY:"",NO_PROXY:"*"}});
writeFileSync(resolve(output,"actual-runtime-tests.txt"),result.stdout+result.stderr);
console.log(result.stdout);if(result.stderr)console.error(result.stderr);
assert.equal(result.status,0,"Actual assembled runtime regressions failed");
const junit=readFileSync(resolve(output,"actual-runtime-junit.xml"),"utf8");
const total=Number(junit.match(/<testsuites\b[^>]*\btests="(\d+)"/)?.[1]);assert.ok(total>0);
writeFileSync(resolve(output,"actual-runtime-verification.json"),JSON.stringify({passed:true,tests:total,manifestSha256:createHash("sha256").update(readFileSync(resolve(candidate,"web-manifest.json"))).digest("hex"),syntaxCheckedNewModules:Object.keys(manifest.newModules).length,testFiles,actualAuthAndJsonModuleImported:true,actualAdapterConstructorRefreshAndStreamExtracted:true,actualResumeClientExtracted:true,noBrowserMount:true,noProductionOrModelCalls:true},null,2)+"\n");
