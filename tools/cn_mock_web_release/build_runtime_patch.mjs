/** Narrow CN mock source patch over the byte-pinned running page module. */
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';

export const ROOT=resolve(fileURLToPath(new URL('../..',import.meta.url)));
export const sha=b=>createHash('sha256').update(b).digest('hex');
export const PAGE='assets/MockInterviewPage-411e4a78.js';
export const CSS='assets/MockInterviewPage-Df2hZMmA.css';
export const VOICE='assets/cn-mock-voice-source.js';
const SOURCES=['apps/web/src/MockInterviewPage.tsx','apps/web/src/mock-interview-client.ts','apps/web/src/mock-interview.css'];
export function parse(text,name='module.js') {
  const tree=ts.createSourceFile(name,text,ts.ScriptTarget.Latest,true,name.endsWith('.tsx')?ts.ScriptKind.TSX:name.endsWith('.ts')?ts.ScriptKind.TS:ts.ScriptKind.JS);
  assert.equal(tree.parseDiagnostics.length,0,`Invalid syntax ${name}`);return tree;
}
export const one=(items,label)=>{assert.equal(items.length,1,`Ambiguous ${label}: ${items.length}`);return items[0];};
const vars=tree=>tree.statements.filter(ts.isVariableStatement).flatMap(n=>n.declarationList.declarations);
const variable=(tree,name)=>one(vars(tree).filter(n=>n.name.getText(tree)===name),name);
const func=(tree,name)=>one(tree.statements.filter(n=>ts.isFunctionDeclaration(n)&&n.name?.text===name),name);
export function compile(text,name='source.ts') {
  const output=ts.transpileModule(text,{fileName:name,reportDiagnostics:true,compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.ES2020,jsx:ts.JsxEmit.React,jsxFactory:'__cnJsx',jsxFragmentFactory:'__cnFragment',removeComments:true}});
  assert.ok(!output.diagnostics?.some(n=>n.category===ts.DiagnosticCategory.Error),'Source transpilation failed');
  parse(output.outputText);return output.outputText;
}
const value=(tree,name)=>variable(tree,name).initializer.getText(tree);
const literalMap=node=>Object.fromEntries(node.properties.map(p=>[p.name.getText(),p.initializer.text]));

export function makePatch(base,sourceManifest) {
  assert.deepEqual(Object.keys(sourceManifest.web).sort(),SOURCES.toSorted(),'Unexpected source handoff scope');
  const files=Object.fromEntries(SOURCES.map(name=>[name,readFileSync(resolve(ROOT,name),'utf8')]));
  for(const name of SOURCES) assert.equal(sha(files[name]),sourceManifest.web[name],`Frozen source drift: ${name}`);
  const original=base[PAGE]; assert.equal(typeof original,'string','Missing active mock page');
  const tree=parse(original),page=func(tree,'ie'),report=func(tree,'ae'),indicator=func(tree,'re');
  assert.ok(original.endsWith('export { ie as MockInterviewPage, ae as MockReportView, _ as mockPhaseLabel };\n'),'Unexpected active mock exports');
  assert.ok(original.startsWith('import { n as e, t } from "./jsx-runtime-2Zwg-L3c.js";'),'React runtime bridge changed');
  assert.ok(original.includes('import { F as n, L as r, R as i, S as a, b as o, x as s } from "./main-559fbe0b.js";'),'Runtime helper bridge changed');
  assert.ok(original.includes('import { t as c } from "./auth-client-bd5688ab.js";'),'Auth bridge changed');
  const source=parse(files[SOURCES[0]],SOURCES[0]);
  assert.deepEqual(literalMap(variable(source,'mockPhaseLabel').initializer),literalMap(variable(tree,'_').initializer),'Phase labels drift');
  const js=parse(compile(files[SOURCES[0]],'MockInterviewPage.tsx'));
  const body=func(js,'MockInterviewPage').body.getText(js);
  const binding={useCallback:'te',useEffect:'u',useState:'d',useRef:'f',Link:'n',useNavigate:'r',useParams:'i',authClient:'c',mockRequest:'s',mockSocketUrl:'a',nextMockQuoteRefreshDelay:'ne',MockVoicePlayer:'__cnMockVoicePlayer',MockPlaybackError:'__cnMockPlaybackError',MockPlaybackIndicator:'re',mockPhaseLabel:'_',MockReportView:'ae',__cnJsx:'e().createElement',__cnFragment:'h'};
  const prefix=Object.entries(binding).map(([name,target])=>`const ${name}=${target};`).join('\n')+
    `\nconst errorText=${value(js,'errorText')};\nconst playbackRecoveryMessage=${value(js,'playbackRecoveryMessage')};\n`;
  const replacement='{\n'+prefix+body.slice(1);
  const before=page.body.getText(tree);
  const patched=original.slice(0,page.body.getStart(tree))+replacement+original.slice(page.body.end);
  assert.equal(patched.replace(replacement,before),original,'Page patch altered unapproved bytes');
  const imports=`import {MockVoicePlayer as __cnMockVoicePlayer,MockPlaybackError as __cnMockPlaybackError} from './cn-mock-voice-source.js';\n`;
  const newPage=imports+patched;parse(newPage);
  assert.ok(newPage.includes(report.getText(tree))&&newPage.includes(indicator.getText(tree)),'Report or indicator changed');
  const client=parse(files[SOURCES[1]],SOURCES[1]);
  const classNode=name=>one(client.statements.filter(n=>ts.isClassDeclaration(n)&&n.name?.text===name),name).getText(client);
  const voice=compile(`const MOCK_WAVEFORM_BARS=${value(client,'MOCK_WAVEFORM_BARS')};\nconst idlePlayback=${value(client,'idlePlayback')};\n${classNode('MockPlaybackError')}\n${classNode('MockVoicePlayer')}`);
  assert.ok(!parse(voice).statements.some(ts.isImportDeclaration),'Voice patch must be self-contained');
  const rules=files[SOURCES[2]].match(/^\.mock-instructions[^\n]*\{[^{}]*\}$/gm)??[];
  assert.equal(rules.length,3,'Only approved compact-instructions CSS may change');
  assert.ok(!base[CSS].includes('.mock-instructions'),'Instructions CSS already exists');
  const css=base[CSS]+'\n'+rules.join('\n')+'\n';
  return {modules:{[PAGE]:newPage,[CSS]:css,[VOICE]:voice},report:{
    sourceFiles:sourceManifest.web,sourceHandoffRelease:sourceManifest.release,
    patchedOriginalModules:[PAGE,CSS],addedSourceModules:[VOICE],
    sourceGeneration:'AST-selected frozen page body and player, ES2020 classic JSX over original React; original transports/router/report/indicator retained',
    pageEdit:{start:page.body.getStart(tree),end:page.body.end,beforeSha256:sha(before),afterSha256:sha(replacement)},
    originalReportSha256:sha(report.getText(tree)),originalIndicatorSha256:sha(indicator.getText(tree)),
    preservedWordExport:'assets/mock-interview-word-export-BOxeSAD1.js',cssAddedRules:rules,
    runtimeBindings:binding,fullSourceAppBundleUsed:false,unmodifiedPageBytesOutsideBody:true,
  }};
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const [baseline,handoff,output]=process.argv.slice(2);assert.ok(baseline&&handoff&&output,'Usage: build_runtime_patch.mjs baseline source-handoff output');
  const base=Object.fromEntries([PAGE,CSS].map(n=>[n,readFileSync(resolve(baseline,n),'utf8')]));
  const result=makePatch(base,JSON.parse(readFileSync(handoff,'utf8')));
  for(const [name,text]of Object.entries(result.modules)){const target=resolve(output,name);mkdirSync(dirname(target),{recursive:true});writeFileSync(target,text);}
  writeFileSync(resolve(output,'patch-report.json'),JSON.stringify(result.report,null,2)+'\n');
  console.log(JSON.stringify({patched:result.report.patchedOriginalModules,added:result.report.addedSourceModules}));
}
