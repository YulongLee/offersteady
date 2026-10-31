/** Extract the approved state-read source into narrow patches of verified CN modules.
 * No network, production configuration or full-app bundle is used here.
 */
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const ROOT = resolve(fileURLToPath(new URL("../..", import.meta.url)));
const sha = s => createHash("sha256").update(s).digest("hex");
const parse = (text, path = "module.js") => {
  const tree = ts.createSourceFile(path, text, ts.ScriptTarget.Latest, true,
    path.endsWith(".tsx") ? ts.ScriptKind.TSX : path.endsWith(".ts") ? ts.ScriptKind.TS : ts.ScriptKind.JS);
  assert.equal(tree.parseDiagnostics.length, 0, `Invalid module ${path}`);
  return tree;
};
const descendants = (tree, predicate) => {
  const found = [];
  function visit(node) { if (predicate(node)) found.push(node); ts.forEachChild(node, visit); }
  visit(tree); return found;
};
const one = (items, description) => { assert.equal(items.length, 1, `Ambiguous ${description}: ${items.length}`); return items[0]; };
const variable = (tree, name) => one(descendants(tree, n => ts.isVariableDeclaration(n) && n.name.getText(tree) === name), name);
const topVariable = (tree, name) => one(tree.statements.filter(ts.isVariableStatement).flatMap(s=>s.declarationList.declarations).filter(n=>n.name.getText(tree)===name),`top-level ${name}`);
const source = name => { const path = resolve(ROOT, name); const text = readFileSync(path, "utf8"); return { text, tree: parse(text, path) }; };
const compile = text => {
  const result = ts.transpileModule(text, { compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ES2020, removeComments: true } });
  assert.ok(!result.diagnostics?.some(d => d.category === ts.DiagnosticCategory.Error));
  return result.outputText.trim();
};
const expression = text => {
  const output = compile(`const __value = (${text});`);
  const tree = parse(output);
  // transpileModule may emit a directive before the variable declaration.
  // Select the initializer from the AST, never strip an assumed text prefix.
  return topVariable(tree, "__value").initializer.getText(tree);
};
const sourceExpression = (s, name) => expression(variable(s.tree, name).initializer.getText(s.tree));
const factory = (expr, bindings, declarations = "") => `(function(){${Object.entries(bindings).map(([name,value])=>`const ${name}=${value};`).join("")}${declarations}\nreturn ${expr};})()`;
const textOf = (tree, node) => tree.text.slice(node.getStart(tree), node.end);

export function applyEdits(text, edits) {
  const ordered = [...edits].sort((a, b) => a.start-b.start || a.end-b.end);
  let end = 0, output = "";
  for (const edit of ordered) {
    assert.ok(edit.start >= end && edit.end >= edit.start, "Overlapping runtime edits");
    assert.equal(text.slice(edit.start, edit.end), edit.before, "Runtime patch anchor changed");
    output += text.slice(end, edit.start)+edit.after; end = edit.end;
  }
  return output+text.slice(end);
}

function editNode(tree, node, after, reason) {
  return { start: node.getStart(tree), end: node.end, before: textOf(tree,node), after, reason };
}

export function makePatches(base, { sourceRoot = ROOT } = {}) {
  assert.equal(sourceRoot, ROOT, "Only the reviewed workspace inputs are allowed");
  const state = source("apps/web/src/state-read-scope.ts");
  const auth = source("apps/web/src/auth-client.ts");
  const api = source("apps/web/src/api-client.ts");
  const backend = source("apps/web/src/backend-adapter.ts");
  const app = source("apps/web/src/App.tsx");
  const sourceManifest = JSON.parse(readFileSync(resolve(ROOT,"artifacts/cn-state-read-local-20261028/candidate-runtime-source-manifest.json")));
  for (const [name, checksum] of Object.entries(sourceManifest.files)) {
    if (name.startsWith("apps/web/")) assert.equal(sha(readFileSync(resolve(ROOT,name))),checksum,`Reviewed source changed: ${name}`);
  }
  const authPath = "assets/auth-client-CpBLJDBI.js", mainPath = "assets/main-0d73b38b.js", resumePath = "assets/ResumeOptimizerPage-131170b3.js";
  for (const name of [authPath,mainPath,resumePath]) assert.equal(typeof base[name],"string",`Missing verified runtime: ${name}`);
  const authTree = parse(base[authPath]), mainTree = parse(base[mainPath]), resumeTree = parse(base[resumePath]);
  // These aliases belong to the byte-pinned active generation. The graph
  // assembler verifies the entire live baseline before this tool runs.
  assert.ok(base[authPath].endsWith("export{l as a,f as i,g as n,i as o,d as r,r as s,P as t};"));
  const statePath = "assets/cn-state-read-scope-source.js";
  const methodsPath = "assets/cn-state-read-methods-source.js";
  const stateJs = compile(state.text);
  const imports = `import {beginStateMutation as __cnBeginStateMutation,stateReadCancelled as __cnStateReadCancelled,isStateReadCancelled as __cnIsStateReadCancelled} from './${statePath.split("/").at(-1)}';\n`;
  const authEdits = [];
  const apiInitializer = topVariable(authTree,"d").initializer;
  assert.ok(textOf(authTree,apiInitializer).includes("无法连接后端基础服务"));
  authEdits.push(editNode(authTree,apiInitializer,factory(sourceExpression(api,"createJsonClient"),{
    AppError:"i",ApiResponseError:"o",isEnvelope:"s",withBaseUrl:"l",defaultFetch:"u",beginStateMutation:"__cnBeginStateMutation",
  }),"Add source-identical request freshness barrier; preserve response/error contract"));
  const helpers = auth.text.slice(auth.text.indexOf("let authGeneration ="), auth.text.indexOf("interface AuthTokensResponse"));
  assert.ok(helpers.includes("window.addEventListener") && helpers.includes("confirmRefreshScope"));
  const storeSession = `const storeSession=${sourceExpression(auth,"storeSession")};`;
  const authInitializer = topVariable(authTree,"P").initializer;
  assert.ok(textOf(authTree,authInitializer).includes("async logout"));
  authEdits.push(editNode(authTree,authInitializer,factory(sourceExpression(auth,"authClient"),{
    client:"_",AppError:"i",readStorageItem:"T",writeStorageItem:"E",removeStorageItem:"D",accountKey:"b",accessTokenKey:"v",refreshTokenKey:"y",
    persistPrototypeAccount:"O",normalizePrototypeAccount:"k",prototypeAuthEnabled:"w",toSafeAccountSummary:"A",authorizationHeaders:"M",queuePromotionClaim:"N",
    stateReadCancelled:"__cnStateReadCancelled",isStateReadCancelled:"__cnIsStateReadCancelled",
  },compile(helpers)+"\n"+storeSession),"Install exact reviewed authentication lifecycle methods, preserving existing API/promotion helpers"));
  const patchedAuth = imports+applyEdits(base[authPath],authEdits);

  const adapterClass = one(descendants(backend.tree,n=>ts.isClassDeclaration(n)&&n.name?.text==="BackendPreviewInterviewAdapter"),"source adapter");
  const stateMethods = ["waitForStateRead","loadScopedState","loadState"].map(name=>one(adapterClass.members.filter(m=>m.name?.getText(backend.tree)===name),name).getText(backend.tree));
  const methodsJs = compile(`import {invalidateStateReads,stateReadCancelled,stateReadGeneration} from './${statePath.split("/").at(-1)}';
export function installStateReadOptimization(adapter,authClient,authHeaders){
 class StateReadMethods { ${stateMethods.join("\n")} }
 adapter.stateReadsInFlight=new Map();
 for(const name of ['waitForStateRead','loadScopedState','loadState']) Object.defineProperty(adapter,name,{value:StateReadMethods.prototype[name],writable:true,configurable:true});
}`);
  const mainEdits=[];
  const refresh = topVariable(mainTree,"di").initializer;
  assert.ok(textOf(mainTree,refresh).includes(".status!==401") && textOf(mainTree,refresh).includes("d.refresh()"));
  mainEdits.push(editNode(mainTree,refresh,factory(sourceExpression(backend,"createAuthRefreshingFetch"),{
    authClient:"d",stateReadCancelled:"__cnStateReadCancelled",
  }),"Replace only refresh wrapper with reviewed lifecycle-aware source"));
  const activeAdapter = one(descendants(mainTree,n=>ts.isClassExpression(n)&&n.members.some(m=>m.name?.getText(mainTree)==="loadState")),"active runtime adapter");
  const stream = one(activeAdapter.members.filter(m=>m.name?.getText(mainTree)==="submitManualAnswerStream"),"stream method");
  const streamStart = one(stream.body.statements.filter(n=>n.getText(mainTree).includes("/api/v1/live-answer/questions/stream")&&n.getText(mainTree).includes("await this.fetchImpl")),"stream transport start");
  const tailStart=streamStart.getStart(mainTree),tailEnd=stream.body.end-1;
  mainEdits.push({start:tailStart,end:tailEnd,before:base[mainPath].slice(tailStart,tailEnd),after:`const __cnEndMutation=__cnBeginStateMutation('/api/v1/live-answer/questions/stream','POST');try{${base[mainPath].slice(tailStart,tailEnd)}}finally{__cnEndMutation();}`,reason:"Wrap original unmodified stream parser/settlement lifecycle in freshness barrier"});
  const provider = one(mainTree.statements.filter(n=>ts.isFunctionDeclaration(n)&&n.name?.text==="H"),"active provider");
  const providerCallback = one(descendants(provider,n=>ts.isArrowFunction(n)&&n.getText(mainTree).includes("new AbortController")&&n.getText(mainTree).includes(".loadState(")&&n.parameters.length===0),"initialization effect");
  const sourceProvider=one(app.tree.statements.filter(n=>ts.isFunctionDeclaration(n)&&n.name?.text==="PrototypeProvider"),"source provider");
  const sourceCallback=one(descendants(sourceProvider,n=>ts.isArrowFunction(n)&&n.getText(app.tree).includes("new AbortController")&&n.getText(app.tree).includes("interviewAppAdapter.loadState")&&n.parameters.length===0),"source effect");
  mainEdits.push(editNode(mainTree,providerCallback,factory(expression(sourceCallback.getText(app.tree)),{
    initialState:"n",authClient:"d",setAuthenticatedState:"o",interviewAppAdapter:"F",loadAttempt:"f",setState:"c",setLoadError:"u",isStateReadCancelled:"__cnIsStateReadCancelled",
  }),"Apply reviewed identity-cancellation retry and explicit refresh to existing provider effect"));
  const logout=one(descendants(provider,n=>ts.isPropertyAssignment(n)&&n.name.getText(mainTree)==="logout"),"provider logout");
  const sourceLogout=variable(app.tree,"logout").initializer;
  mainEdits.push(editNode(mainTree,logout.initializer,factory(expression(sourceLogout.getText(app.tree)),{
    authClient:"d",setAuthenticated:"g",setState:"c",interviewAppAdapter:"F",
  }),"Preserve newer login if old logout finishes late"));
  const installAnchor="__installWrittenMultiScreen(F,{AppError:c,authHeaders:N,requireUserId:P,screenshotStageToTask:ji,screenshotAnswerText:ki,toSubmitScreenshotAnswerResult:Ai});";
  assert.equal(base[mainPath].split(installAnchor).length,2,"Written multi-screen setup anchor changed");
  const at=base[mainPath].indexOf(installAnchor)+installAnchor.length;
  mainEdits.push({start:at,end:at,before:"",after:"__cnInstallStateReads(F,d,N);",reason:"Install only three state-read methods on the existing adapter, retaining all other methods and multi-screen extension"});
  const patchedMain=imports+`import {installStateReadOptimization as __cnInstallStateReads} from './${methodsPath.split("/").at(-1)}';\n`+applyEdits(base[mainPath],mainEdits);

  const resumeEdits=[];
  const responseMethod=one(descendants(resumeTree,n=>ts.isMethodDeclaration(n)&&n.name?.getText(resumeTree)==="response"&&n.getText(resumeTree).includes("无法连接简历优化服务")),"resume response method");
  const responseBody=base[resumePath].slice(responseMethod.body.getStart(resumeTree)+1,responseMethod.body.end-1);
  resumeEdits.push({start:responseMethod.body.getStart(resumeTree)+1,end:responseMethod.body.end-1,before:responseBody,after:`const __cnEndMutation=__cnBeginStateMutation(\`/api/v1/resume-optimizer\${e}\`,t.method);try{${responseBody}}finally{__cnEndMutation();}`,reason:"Wrap original resume client transport in shared freshness barrier"});
  const refreshMaterials=variable(resumeTree,"We").initializer;
  assert.ok(refreshMaterials.getText(resumeTree).includes("await n.loadState(e)"));
  const refreshed=refreshMaterials.getText(resumeTree).replace("async (e = Y())", "async (e = Y(), __cnForceRefresh = false)").replace("n.loadState(e)","n.loadState(e, {forceRefresh: __cnForceRefresh})");
  assert.notEqual(refreshed,refreshMaterials.getText(resumeTree));
  resumeEdits.push(editNode(resumeTree,refreshMaterials,refreshed,"Explicit refresh bypasses the in-flight wave"));
  const manualRefresh=one(descendants(resumeTree,n=>ts.isArrowFunction(n)&&n.modifiers?.some(m=>m.kind===ts.SyntaxKind.AsyncKeyword)&&n.parameters.length===0&&n.getText(resumeTree).includes('B("资料已刷新。")')&&n.getText(resumeTree).length<300),"manual materials refresh action");
  const beforeManual=manualRefresh.getText(resumeTree);
  assert.equal(beforeManual.split("await We()").length,2);
  resumeEdits.push(editNode(resumeTree,manualRefresh,beforeManual.replace("await We()","await We(Y(), true)"),"Use force refresh only on explicit materials refresh click"));
  const patchedResume=imports+applyEdits(base[resumePath],resumeEdits);
  const modules={ [authPath]:patchedAuth,[mainPath]:patchedMain,[resumePath]:patchedResume,[statePath]:stateJs,[methodsPath]:methodsJs };
  for(const [name,text] of Object.entries(modules)) parse(text,name);
  return { modules, report:{
    sourceFiles:Object.fromEntries(Object.keys(sourceManifest.files).filter(n=>n.startsWith("apps/web/")).map(n=>[n,sha(readFileSync(resolve(ROOT,n)))])),
    sourceGeneration:"TypeScript ES2020 transpilation of reviewed source expressions/methods; original runtime retained around bounded edits",
    patchedOriginalModules:[authPath,mainPath,resumePath],addedSourceModules:[statePath,methodsPath],
    edits:{[authPath]:authEdits,[mainPath]:mainEdits,[resumePath]:resumeEdits},
    originalStreamParserRetained:true,existingWrittenMultiScreenSetupRetained:true,
    unmodifiedRuntimeOutsideRecordedEdits:true,fullSourceAppBundleUsed:false,
  }};
}

if (process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const [baseline, output] = process.argv.slice(2); assert.ok(baseline&&output,"Usage: build_runtime_patch.mjs <baseline/html> <output>");
  const names=["assets/auth-client-CpBLJDBI.js","assets/main-0d73b38b.js","assets/ResumeOptimizerPage-131170b3.js"];
  const result=makePatches(Object.fromEntries(names.map(n=>[n,readFileSync(resolve(baseline,n),"utf8")])));
  mkdirSync(output,{recursive:true});
  for(const [name,text] of Object.entries(result.modules)){const path=resolve(output,name);mkdirSync(resolve(path,".."),{recursive:true});writeFileSync(path,text);}
  writeFileSync(resolve(output,"patch-report.json"),JSON.stringify(result.report,null,2)+"\n");
  console.log(JSON.stringify({patchedOriginals:result.report.patchedOriginalModules,addedModules:result.report.addedSourceModules,sourceBaselineVerified:true}));
}
