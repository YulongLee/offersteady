/** Exercise the actual patched initialization/logout/manual-refresh expressions
 * without rendering React, a production account, or an external request.
 */
import assert from "node:assert/strict";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import ts from "typescript";

const [candidateArg, outputArg]=process.argv.slice(2); assert.ok(candidateArg&&outputArg);
const candidate=resolve(candidateArg), output=resolve(outputArg);mkdirSync(output,{recursive:true});
const manifest=JSON.parse(readFileSync(resolve(candidate,"web-manifest.json")));
const runtime=from=>resolve(candidate,"web/html",manifest.moduleMapping[from]);
const state=await import(pathToFileURL(runtime("assets/cn-state-read-scope-source.js")).href);
const parse=path=>ts.createSourceFile(path,readFileSync(path,"utf8"),ts.ScriptTarget.Latest,true,ts.ScriptKind.JS);
const tree=parse(runtime("assets/main-0d73b38b.js"));
const all=(root,predicate)=>{const found=[];function visit(n){if(predicate(n))found.push(n);ts.forEachChild(n,visit)}visit(root);return found;};
const one=(items,label)=>{assert.equal(items.length,1,label);return items[0];};
const provider=one(tree.statements.filter(n=>ts.isFunctionDeclaration(n)&&n.name?.text==="H"),"provider");
const effect=one(all(provider,n=>ts.isArrowFunction(n)&&n.getText(tree).includes("new AbortController")&&n.getText(tree).includes("interviewAppAdapter.loadState")&&n.parameters.length===0),"actual effect");
// Its factory contains the reviewed source aliases, whose outer actual names
// are supplied as test-only dependencies. The expression itself is unmodified.
let factory=effect.parent;
while(factory.parent&&!ts.isCallExpression(factory))factory=factory.parent;
assert.ok(ts.isCallExpression(factory));
const effectFactory=Function("n","d","o","F","f","c","u","__cnIsStateReadCancelled",`return (${factory.getText(tree)});`);
const sleep=()=>new Promise(r=>setTimeout(r,0));
const flush=async()=>{await sleep();await sleep();};
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no});return{promise,resolve,reject};};
const run=({auth,adapter,attempt=0})=>{
 const states=[],errors=[],authenticated=[];
 const callback=effectFactory(null,auth,v=>authenticated.push(v),adapter,attempt,v=>states.push(v),v=>errors.push(v),state.isStateReadCancelled);
 const cleanup=callback(); return {cleanup,states,errors,authenticated};
};
const passed=[];
for(const stage of ["restore","loadState"]){
 const pending=deferred();let current={account:{id:"synthetic-a"}},restoreCalls=0,loadCalls=0,clears=0;
 const auth={readStoredSession:()=>current,clear:()=>{clears++;current=null;},restore:async()=>{restoreCalls++;return stage==="restore"&&restoreCalls===1?pending.promise:current;}};
 const adapter={loadState:async()=>{loadCalls++;return stage==="loadState"&&loadCalls===1?pending.promise:{account:current.account};}};
 const result=run({auth,adapter});await flush();current={account:{id:"synthetic-b"}};pending.reject(state.stateReadCancelled());await flush();
 assert.equal(clears,0);assert.equal(restoreCalls,2);assert.equal(result.states.at(-1).account.id,"synthetic-b");assert.ok(result.errors.every(value=>value===""));result.cleanup();passed.push(`new identity preserved after ${stage} cancellation`);
}
{
 const pending=deferred();let restores=0,loads=0;
 const auth={readStoredSession:()=>({account:{id:"synthetic"}}),clear:()=>assert.fail("cleanup cannot clear auth"),restore:()=>{restores++;return pending.promise;}};
 const result=run({auth,adapter:{loadState:async()=>{loads++;return{};}}});result.cleanup();pending.reject(state.stateReadCancelled());await flush();
 assert.equal(restores,1);assert.equal(loads,0);assert.deepEqual(result.states,[]);passed.push("effect cleanup does not restart cancelled work");
}
{
 const options=[];const account={account:{id:"synthetic"}};
 const result=run({attempt:1,auth:{readStoredSession:()=>account,restore:async()=>account},adapter:{loadState:async(_signal,o)=>{options.push(o);return account;}}});await flush();
 assert.deepEqual(options,[{forceRefresh:true}]);assert.deepEqual(result.states,[account]);result.cleanup();passed.push("explicit initial retry requests forceRefresh");
}
{
 let current={account:{id:"synthetic"}},clears=0;const options=[];
 const result=run({auth:{readStoredSession:()=>current,restore:async()=>{throw Error("Synthetic expired auth");},clear:()=>{current=null;clears++;}},adapter:{loadState:async(_signal,o)=>{options.push(o);return{account:null};}}});await flush();
 assert.equal(clears,1);assert.deepEqual(options,[{auth:false}]);assert.equal(result.states.at(-1).account,null);result.cleanup();passed.push("ordinary auth failure retains anonymous recovery");
}
{
 const logout=one(all(provider,n=>ts.isPropertyAssignment(n)&&n.name.getText(tree)==="logout"),"actual logout");
 const gate=deferred(),updates=[];let current={account:{id:"synthetic-a"}};
 const auth={logout:()=>gate.promise,readStoredSession:()=>current};
 const action=Function("d","g","c","F",`return (${logout.initializer.getText(tree)});`)(auth,v=>updates.push(v),()=>assert.fail("late logout cannot change state"),{});
 const pending=action();current={account:{id:"synthetic-b"}};gate.resolve();await pending;assert.deepEqual(updates,[]);passed.push("late logout preserves new login in provider");
}
{
 const resume=parse(runtime("assets/ResumeOptimizerPage-131170b3.js"));
 const refresh=one(all(resume,n=>ts.isVariableDeclaration(n)&&n.name.getText(resume)==="We"),"actual materials refresh");
 const signal=new AbortController().signal,options=[],updates=[];
 const refreshFunction=Function("n","Y","X","t",`return (${refresh.initializer.getText(resume)});`)({loadState:async(s,o)=>{assert.equal(s,signal);options.push(o);return{ready:true};}},()=>signal,()=>true,v=>updates.push(v));
 const action=one(all(resume,n=>ts.isArrowFunction(n)&&n.modifiers?.some(m=>m.kind===ts.SyntaxKind.AsyncKeyword)&&n.getText(resume).includes('B("资料已刷新。")')&&n.getText(resume).length<300),"actual manual refresh");
 const messages=[];await Function("We","Y","X","B",`return (${action.getText(resume)});`)(refreshFunction,()=>signal,()=>true,v=>messages.push(v))();
 assert.deepEqual(options,[{forceRefresh:true}]);assert.deepEqual(updates,[{ready:true}]);assert.deepEqual(messages,["资料已刷新。"]);passed.push("actual resume refresh button forces a fresh state request");
}
const report={passed:true,cases:passed.length,results:passed,actualRuntimeExpressions:true,productionWrites:0,externalCalls:0};
writeFileSync(resolve(output,"actual-initialization-verification.json"),JSON.stringify(report,null,2)+"\n");
console.log(JSON.stringify(report,null,2));
