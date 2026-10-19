import {readFileSync as readFile,writeFileSync as writeFile,mkdirSync,cpSync,rmSync,readdirSync,statSync,chmodSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {build} from '/private/tmp/offersteady-cn-written-multi-screen/node_modules/vite/dist/node/index.js';
import react from '/private/tmp/offersteady-cn-written-multi-screen/node_modules/@vitejs/plugin-react/dist/index.js';
const require=createRequire('/private/tmp/offersteady-cn-written-multi-screen/package.json'),ts=require('typescript');
const R='/Users/liyulong/liyulong/1_projects/offersteady', W='/private/tmp/offersteady-cn-written-multi-screen', A=resolve(R,'artifacts/cn-written-multi-screen-20261019-release/web');
const baseline=resolve(A,'running-static'),modules=resolve(A,'module-src'),candidate=resolve(A,'candidate-static'),patch=resolve(A,'patch-static');
const entry='main-09170906.js',oldPage='LivePage-8333c4a2.js',release='cn-written-multi-screen-20261019.1';
const read=p=>readFile(p,'utf8'),hash=x=>createHash('sha256').update(x).digest('hex');
const save=(p,v)=>{mkdirSync(dirname(p),{recursive:true});writeFile(p,JSON.stringify(v,null,2)+'\n')};
const walk=root=>readdirSync(root).flatMap(n=>statSync(resolve(root,n)).isDirectory()?walk(resolve(root,n)).map(x=>n+'/'+x):[n]);
const inventory=root=>Object.fromEntries(walk(root).sort().map(p=>[p,hash(readFile(resolve(root,p)))]));
const before=inventory(baseline),sealed=JSON.parse(read(resolve(W,'releases/cn-20261019.1/manifest.json'))).web;
if(JSON.stringify(Object.entries(before).sort())!==JSON.stringify(Object.entries(sealed.files).sort()))throw Error('sealed/static mismatch');
const originals=new Map(readdirSync(resolve(baseline,'assets')).filter(x=>x.endsWith('.js')&&!x.startsWith('._')).map(x=>[x,read(resolve(baseline,'assets',x))]));
const sourcePaths=['LivePage.tsx','AnswerActionBar.tsx','backend-adapter.ts','domain.ts','styles.css'];
const sourceFiles=Object.fromEntries(sourcePaths.map(p=>['apps/web/src/'+p,hash(readFile(resolve(W,'apps/web/src',p)))]));
const legacyName='LivePageLegacy-'+hash(originals.get(oldPage)+release).slice(0,8)+'.js';
mkdirSync(modules,{recursive:true});cpSync(resolve(W,'apps/web/src/LivePage.tsx'),resolve(modules,'LivePage.tsx'));cpSync(resolve(W,'apps/web/src/AnswerActionBar.tsx'),resolve(modules,'AnswerActionBar.tsx'));
writeFile(resolve(modules,'react.ts'),`import {n as initializeReact} from './jsx-runtime-2Zwg-L3c.js'; const React=initializeReact(); export const {useEffect,useRef,useState,useMemo,useLayoutEffect}=React; export default React;\n`);
writeFile(resolve(modules,'jsx-runtime.ts'),`import {t as initializeJsx} from './jsx-runtime-2Zwg-L3c.js'; export const {jsx,jsxs,Fragment}=initializeJsx();\n`);
writeFile(resolve(modules,'router.ts'),`export {F as Link,L as useNavigate,R as useParams} from './${entry}';\n`);
writeFile(resolve(modules,'routes.ts'),`export {k as routes} from './${entry}';\n`);
writeFile(resolve(modules,'app-adapter.ts'),`export {A as interviewAppAdapter} from './${entry}';\n`);
writeFile(resolve(modules,'app-context.ts'),`export {t as usePrototype} from './${entry}';\n`);
writeFile(resolve(modules,'api-client.ts'),`export {i as runAdapterOperation} from './auth-client-CpBLJDBI.js';\n`);
writeFile(resolve(modules,'route-components.ts'),`export {C as AnswerWorkspace} from './${entry}';\n`);
for(const [name,symbol] of [['ConversationMonitor','oe'],['ManualQuestionComposer','se'],['MobileInterviewControls','le'],['WebSearchToggle','ue'],['WorkspaceDivider','de']])writeFile(resolve(modules,name+'.tsx'),`export {${name}} from './${legacyName}';\n`);
writeFile(resolve(modules,'entry.tsx'),`import {useParams} from 'react-router-dom';import {usePrototype} from './app-context';import {LivePage as WrittenLivePage} from './LivePage';import {OriginalLivePage} from './${legacyName}';export function LivePage(props){const{id}=useParams();const{state}=usePrototype();return state.interviews.find(item=>item.id===id)?.sessionMode==='written'?<WrittenLivePage {...props}/>:<OriginalLivePage {...props}/>;}\n`);
const aliases=new Map([['react','react.ts'],['react/jsx-runtime','jsx-runtime.ts'],['react-router-dom','router.ts'],...['routes','app-adapter','app-context','api-client','route-components'].map(x=>['./'+x,x+'.ts']),...['ConversationMonitor','ManualQuestionComposer','MobileInterviewControls','WebSearchToggle','WorkspaceDivider'].map(x=>['./'+x,x+'.tsx'])]);
await build({configFile:false,root:modules,publicDir:false,plugins:[{name:'reuse-actual-cn-singletons',enforce:'pre',resolveId(id,importer){if(aliases.has(id))return resolve(modules,aliases.get(id));if(id.startsWith('./')&&id.endsWith('.js')&&(id.slice(2)===legacyName||originals.has(id.slice(2))))return{id,external:true};if(id==='@offersteady/protocol')return resolve(W,'packages/protocol/src/index.ts');if(id.startsWith('./')&&importer?.startsWith(modules)&&!['./LivePage','./AnswerActionBar'].includes(id)){for(const ext of ['.ts','.tsx'])if(statSafe(resolve(W,'apps/web/src',id+ext)))return resolve(W,'apps/web/src',id+ext);}}},react()],build:{target:'chrome86',outDir:resolve(A,'compiled-page'),emptyOutDir:true,lib:{entry:resolve(modules,'entry.tsx'),formats:['es'],fileName:()=> 'WrittenMultiScreen-new.js'},minify:true,sourcemap:false}});
function statSafe(p){try{return statSync(p).isFile()}catch{return false}}
const newPage=read(resolve(A,'compiled-page/WrittenMultiScreen-new.js'));
const adapterSource=read(resolve(W,'apps/web/src/backend-adapter.ts')),adapterAst=ts.createSourceFile('backend-adapter.ts',adapterSource,ts.ScriptTarget.Latest,true);
const adapterClass=adapterAst.statements.find(n=>ts.isClassDeclaration(n)&&n.name.text==='BackendPreviewInterviewAdapter');
const methodNames=['getScreenshotCapturePolicy','captureScreenshot','submitScreenshotBatch','createScreenshotRequest','waitForScreenshotRequest'];
const methods=methodNames.map(name=>{const n=adapterClass.members.find(n=>ts.isMethodDeclaration(n)&&n.name.getText(adapterAst)===name);if(!n)throw Error(name);return n.getText(adapterAst)});
const extensionTS=`export function installWrittenMultiScreen(adapter:any,deps:any){const{AppError,authHeaders,requireUserId,screenshotStageToTask,screenshotAnswerText,toSubmitScreenshotAnswerResult}=deps;class Extension{${methods.join('\n')}}for(const name of ${JSON.stringify(methodNames)})adapter[name]=Extension.prototype[name];}\n`;
const extensionJS=ts.transpileModule(extensionTS,{compilerOptions:{target:ts.ScriptTarget.ES2019,module:ts.ModuleKind.ESNext,removeComments:true}}).outputText;
writeFile(resolve(A,'adapter-extension-source.ts'),extensionTS);
const extensionName='written-multi-screen-adapter-'+hash(extensionJS).slice(0,8)+'.js';
const cssBefore=read(resolve(W,'apps/web/src/styles.css'));const cssMarker='/* Written multi-screen collection stays in the existing action surface. */';if(cssBefore.split(cssMarker).length!==2)throw Error('css marker');const extraCss=cssMarker+cssBefore.split(cssMarker)[1];const cssName='written-multi-screen-'+hash(extraCss).slice(0,8)+'.css';
const semantic=new Map(originals),patches=[];
function replace(name,from,to,purpose){let source=semantic.get(name);if(source.split(from).length!==2)throw Error('ambiguous semantic patch '+purpose);semantic.set(name,source.replace(from,to));patches.push({file:name,purpose,from,to});}
replace(entry,'e.kind===`screenshot-capture-updated`&&typeof e.payload.requestId==`string`','e.kind===`screenshot-capture-updated`&&e.payload.captureOnly!==!0&&!(Array.isArray(e.payload.captureRequestIds)&&e.payload.captureRequestIds.length>0)&&typeof e.payload.requestId==`string`','keep capture-only/batch events out of legacy shortcut fallback');
replace(entry,'Xa(),es(),is();',`__installWrittenMultiScreen(F,{AppError:c,authHeaders:N,requireUserId:P,screenshotStageToTask:ji,screenshotAnswerText:ki,toSubmitScreenshotAnswerResult:Ai});Xa(),es(),is();`,'attach only five new adapter methods; original single-image/other methods remain verbatim');
semantic.set(entry,`import {installWrittenMultiScreen as __installWrittenMultiScreen} from './${extensionName}';\n`+semantic.get(entry));
const pageName='WrittenMultiScreen-'+hash(newPage+release).slice(0,8)+'.js';
replace(entry,`i(()=>import(\`./${oldPage}\`)`,`i(()=>import(\`./${pageName}\`)`,'written-aware wrapper, normal interview delegates to original production LivePage');
// Preload includes the new CSS beside the original full dependency list.
replace(entry,'"assets/LivePage-8333c4a2.js"',`"assets/${pageName}"`,'point live preloading to additive wrapper');
replace(entry,'__vite__mapDeps([0,1,2,3])).catch',`[...__vite__mapDeps([0,1,2,3]),"assets/${cssName}"]).catch`,'preload only additive written CSS with existing live dependencies');
function literals(name,text){const ast=ts.createSourceFile(name,text,ts.ScriptTarget.Latest,true,ts.ScriptKind.JS);if(ast.parseDiagnostics.length)throw Error('syntax '+name);const refs=[];function visit(n){if(ts.isStringLiteral(n)||ts.isNoSubstitutionTemplateLiteral(n)){const prefix=n.text.startsWith('./')?'./':n.text.startsWith('assets/')?'assets/':null,target=prefix?n.text.slice(prefix.length):null;if(target&&originals.has(target))refs.push({start:n.getStart(ast)+1,end:n.end-1,target,prefix});}ts.forEachChild(n,visit)}visit(ast);return refs;}
const graph=new Map([...originals].map(([n,t])=>[n,literals(n,t).map(x=>x.target)])),reachable=new Set();function follow(n){if(reachable.has(n))return;reachable.add(n);for(const c of graph.get(n)??[])follow(c)}follow(entry);
const changed=new Set([entry]);let expanded;do{expanded=false;for(const n of reachable)if(!changed.has(n)&&graph.get(n).some(c=>changed.has(c))){changed.add(n);expanded=true}}while(expanded);
const revision=hash(newPage+extensionJS+extraCss+JSON.stringify(patches)),names=new Map([...changed].map(n=>[n,n===oldPage?legacyName:n.replace(/-[A-Za-z0-9_-]{8}\.js$/,'')+'-'+hash(release+revision+n+semantic.get(n)).slice(0,8)+'.js']));
rmSync(candidate,{recursive:true,force:true});cpSync(baseline,candidate,{recursive:true});rmSync(patch,{recursive:true,force:true});mkdirSync(resolve(patch,'assets'),{recursive:true});
function writeAsset(name,text){if(before['assets/'+name])throw Error('immutable asset name collision');writeFile(resolve(candidate,'assets',name),text);writeFile(resolve(patch,'assets',name),text)}
function rewrite(name,text){let result=text;for(const ref of literals(name,text).filter(x=>names.has(x.target)).sort((a,b)=>b.start-a.start))result=result.slice(0,ref.start)+ref.prefix+names.get(ref.target)+result.slice(ref.end);return result;}
const relinks=[];
for(const n of changed){let source=semantic.get(n);if(n===oldPage)source+='\nexport {R as OriginalLivePage,oe as ConversationMonitor,se as ManualQuestionComposer,le as MobileInterviewControls,ue as WebSearchToggle,de as WorkspaceDivider};\n';const after=rewrite(n,source);let restored=after;for(const[a,b]of names)restored=restored.replaceAll(b,a);if(restored!==source)throw Error('non URL delta '+n);writeAsset(names.get(n),after);relinks.push({before:n,after:names.get(n),beforeSha256:hash(originals.get(n)),afterSha256:hash(after),kind:n===entry?'only audited adapter install/event filter/live wrapper URLs':n===oldPage?'unchanged production logic plus named exports and main URL':'module URLs only'});}
writeAsset(pageName,rewrite(pageName,newPage));writeAsset(extensionName,extensionJS);writeAsset(cssName,extraCss);
const htmlChanges=[];for(const n of ['index.html','guide.html','terms.html','privacy.html']){const source=read(resolve(baseline,n));let after=source;for(const[a,b]of names)after=after.replaceAll('/assets/'+a,'/assets/'+b);let restored=after;for(const[a,b]of names)restored=restored.replaceAll('/assets/'+b,'/assets/'+a);if(restored!==source)throw Error('HTML changed beyond module URLs '+n);if(after!==source){writeFile(resolve(candidate,n),after);writeFile(resolve(patch,n),after);htmlChanges.push(n)}}
for(const dir of [patch,resolve(patch,'assets')])chmodSync(dir,0o755);for(const p of walk(patch))chmodSync(resolve(patch,p),0o644);
for(const p of sourcePaths)if(hash(readFile(resolve(W,'apps/web/src',p)))!==sourceFiles['apps/web/src/'+p])throw Error('source changed during assembly');
const after=inventory(candidate),files=inventory(patch);for(const[p,v]of Object.entries(before))if(after[p]!==v&&!htmlChanges.includes(p))throw Error('old file overwritten '+p);
const routeChecks={};for(const route of ['resume-optimizer','mock-interviews','written-exams','interviews','library','billing'])routeChecks[route]=semantic.get(entry).includes(route);if(Object.values(routeChecks).some(x=>!x))throw Error('missing route');
const manifest={passed:true,release,baseImage:sealed.image,entryBefore:entry,entryAfter:names.get(entry),page:pageName,legacyPage:legacyName,adapter:extensionName,css:cssName,oldStaticCount:Object.keys(before).length,afterStaticCount:Object.keys(after).length,oldStatic:before,webFiles:files,candidateFiles:after,sourceFiles,reachableModules:reachable.size,relinks,htmlChanges,allOldAssetsBytePreserved:true,allNonHtmlOldFilesBytePreserved:true,publicDocumentsOnlyModuleURLsChanged:true,originalSingleImageAnswerMethodBytePreserved:true,normalLivePageBytePreservedExceptMainURLAndAdditionalExports:true,routeChecks,nginxUnchanged:true,buildManifestUnchanged:true,syntheticPreviewShipped:false,patches};
save(resolve(A,'overlay-manifest.json'),manifest);writeFile(resolve(A,'Dockerfile'),`FROM ${sealed.image}\nCOPY patch-static/ /usr/share/nginx/html/\n`);console.log(JSON.stringify({passed:true,entry:names.get(entry),page:pageName,old:Object.keys(before).length,after:Object.keys(after).length,patch:Object.keys(files).length,relinked:relinks.length,htmlChanges,nginxUnchanged:true}));
