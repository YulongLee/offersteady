import { spawn } from "node:child_process";
import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { resolveLocalWebUrl } from "./local-web-access.mjs";

const chrome = process.env.CHROME_PATH ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const artifacts = process.env.OFFERSTEADY_REVIEW_ARTIFACTS ?? join(tmpdir(), "offersteady-live-review");
const profile = await mkdtemp(join(tmpdir(), "offersteady-chrome-"));
await mkdir(artifacts, { recursive: true });
const access = await resolveLocalWebUrl();
if (!access.selected) {
  throw new Error([
    "No reachable local web prototype found.",
    ...access.results.map(result => `- ${result.url}: ${result.reason ?? "unreachable"}`),
    "Start npm run dev:web or npm run preview:web before running review:live.",
  ].join("\n"));
}
const baseUrl = access.selected;

const browser = spawn(chrome, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  "--remote-debugging-port=0", `--user-data-dir=${profile}`, `${baseUrl}/login`,
], { stdio: ["ignore", "ignore", "pipe"] });
const stopBrowser = () => { if (!browser.killed) browser.kill("SIGTERM"); };
process.once("exit", stopBrowser);
process.once("SIGINT", () => { stopBrowser(); process.exit(130); });

const devtoolsUrl = await new Promise((resolve, reject) => {
  const timeout = setTimeout(() => reject(new Error("Chrome DevTools startup timed out")), 10_000);
  browser.stderr.setEncoding("utf8");
  browser.stderr.on("data", chunk => {
    const match = chunk.match(/DevTools listening on (ws:\/\/[^\s]+)/);
    if (match) { clearTimeout(timeout); resolve(match[1]); }
  });
  browser.once("exit", code => reject(new Error(`Chrome exited before review (${code})`)));
});

const browserSocket = new WebSocket(devtoolsUrl);
await new Promise((resolve, reject) => { browserSocket.onopen = resolve; browserSocket.onerror = reject; });
let sequence = 0;
const pending = new Map();
browserSocket.onmessage = event => {
  const message = JSON.parse(event.data);
  if (message.id && pending.has(message.id)) {
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    message.error ? reject(new Error(message.error.message)) : resolve(message.result);
  }
};
const browserCommand = (method, params = {}) => new Promise((resolve, reject) => {
  const id = ++sequence; pending.set(id, { resolve, reject });
  browserSocket.send(JSON.stringify({ id, method, params }));
});
const { targetInfos } = await browserCommand("Target.getTargets");
const target = targetInfos.find(item => item.type === "page");
if (!target) throw new Error("No Chrome page target found");
const { sessionId } = await browserCommand("Target.attachToTarget", { targetId: target.targetId, flatten: true });
const command = (method, params = {}) => new Promise((resolve, reject) => {
  const id = ++sequence; pending.set(id, { resolve, reject });
  browserSocket.send(JSON.stringify({ id, sessionId, method, params }));
});
const pause = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
const evaluate = async expression => {
  const result = await command("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  if (result.exceptionDetails) throw new Error(`${result.exceptionDetails.text}: ${result.exceptionDetails.exception?.description ?? "unknown browser exception"}`);
  return result.result.value;
};
const assert = (condition, message) => { if (!condition) throw new Error(message); };

await command("Runtime.enable");
await command("Page.enable");
await command("Accessibility.enable");
await pause(700);
const commercialResults = [];
for (const viewport of [{ name: "phone", width: 390, height: 844 }, { name: "tablet", width: 820, height: 1180 }, { name: "desktop", width: 1440, height: 900 }]) {
  await command("Emulation.setDeviceMetricsOverride", { width: viewport.width, height: viewport.height, deviceScaleFactor: viewport.width < 1000 ? 2 : 1, mobile: viewport.width < 1000 });
  await command("Page.navigate", { url: `${baseUrl}/` }); await pause(350);
  const landing = await evaluate(`({ width: document.documentElement.scrollWidth, heading: document.querySelector('.value-proof h2')?.textContent, benefits: document.querySelectorAll('.value-proof-grid article').length, hasLegacyBoundary: document.body.textContent.includes('CLEAR BOUNDARIES') })`);
  assert(landing.width <= viewport.width + 1, `landing ${viewport.name}: horizontal overflow`); assert(landing.benefits === 3 && !landing.hasLegacyBoundary, `landing ${viewport.name}: value hierarchy missing`);
  commercialResults.push({ page: "landing", ...viewport, ...landing });
  const shot = await command("Page.captureScreenshot", { format: "png", captureBeyondViewport: false }); await writeFile(join(artifacts, `landing-${viewport.name}.png`), Buffer.from(shot.data, "base64"));
}
await evaluate(`localStorage.setItem('offersteady.prototype.auth', 'true')`);
await command("Page.navigate", { url: `${baseUrl}/app` });
await pause(500);
const continuation = await evaluate(`({ continueActions: [...document.querySelectorAll('a')].filter(node => node.textContent.trim() === '继续面试').length, hasPreview: document.body.textContent.includes('预览工作台'), hasContinuePreparation: [...document.querySelectorAll('a')].some(node => node.textContent.trim() === '继续准备') })`);
assert(continuation.continueActions === 1 && !continuation.hasPreview && !continuation.hasContinuePreparation, `dashboard: continuation actions are not streamlined ${JSON.stringify(continuation)}`);

const scenarios = [
  { name: "phone", width: 390, height: 844, mobile: true },
  { name: "tablet", width: 820, height: 1180, mobile: true },
  { name: "desktop-1200", width: 1200, height: 820, mobile: false },
  { name: "desktop-1440", width: 1440, height: 900, mobile: false },
  { name: "zoom-200", width: 640, height: 900, mobile: false },
  { name: "narrow-landscape", width: 667, height: 375, mobile: true },
];
const results = [];

for (const scenario of scenarios) {
  await command("Emulation.setDeviceMetricsOverride", {
    width: scenario.width, height: scenario.height, deviceScaleFactor: scenario.mobile ? 2 : 1, mobile: scenario.mobile,
  });
  await evaluate(`history.pushState({}, '', '/app'); dispatchEvent(new PopStateEvent('popstate'))`);
  await pause(80);
  await evaluate(`history.pushState({}, '', '/app/interviews/demo/live'); dispatchEvent(new PopStateEvent('popstate'))`);
  await pause(250);
  const metrics = await evaluate(`(() => {
    const rect = selector => { const node = document.querySelector(selector); if (!node) return null; const value = node.getBoundingClientRect(); return { top: value.top, bottom: value.bottom, left: value.left, right: value.right, width: value.width, height: value.height }; };
    const actions = [...document.querySelectorAll('.compact-question-bar button')].map(node => ({ name: node.getAttribute('aria-label') || node.textContent.trim(), ...rect('#' + (node.id || (node.id = 'review-' + Math.random().toString(16).slice(2)))) }));
    return {
      innerWidth, innerHeight, bodyScrollWidth: document.documentElement.scrollWidth,
      conversation: rect('.conversation-monitor'), answer: rect('.answer-workspace'), actionBar: rect('.compact-question-bar'), separator: rect('.workspace-divider'), actions,
      roleLabels: [...document.querySelectorAll('.conversation-turn-meta strong')].map(node => node.textContent.trim()),
      hasRolePending: document.body.textContent.includes('角色待确认'),
      roleCorrectionButtons: [...document.querySelectorAll('button')].filter(node => /设为面试官|设为我/.test(node.textContent)).length,
      hasMaterialRail: Boolean(document.querySelector('.material-rail, #live-material-rail, .material-toggle')),
      historyDrawer: Boolean(document.querySelector('.live-right, [aria-label*=历史][role=navigation]')),
    };
  })()`);
  assert(metrics.conversation && metrics.answer && metrics.actionBar, `${scenario.name}: required regions missing`);
  if (scenario.width >= 1051) {
    assert(metrics.separator, `${scenario.name}: desktop separator missing`);
    assert(metrics.conversation.right <= metrics.separator.left + 1 && metrics.separator.right <= metrics.answer.left + 1, `${scenario.name}: conversation and answer are not left/right columns ${JSON.stringify(metrics)}`);
    assert(metrics.actionBar.left >= metrics.answer.left - 1, `${scenario.name}: actions escaped the answer column`);
  } else {
    assert(!metrics.separator, `${scenario.name}: narrow layout exposes desktop separator`);
    assert(metrics.conversation.top < metrics.answer.top && metrics.answer.top < metrics.actionBar.top, `${scenario.name}: narrow content order changed ${JSON.stringify(metrics)}`);
  }
  assert(metrics.bodyScrollWidth <= metrics.innerWidth + 1, `${scenario.name}: horizontal overflow (${metrics.bodyScrollWidth}/${metrics.innerWidth})`);
  assert(!metrics.hasMaterialRail, `${scenario.name}: live material rail returned`);
  assert(!metrics.historyDrawer, `${scenario.name}: legacy history drawer returned`);
  assert(metrics.roleLabels.every(label => label === '我' || label === '面试官') && !metrics.hasRolePending && metrics.roleCorrectionButtons === 0, `${scenario.name}: transcript exposed a third role ${JSON.stringify(metrics.roleLabels)}`);
  if (scenario.name !== "narrow-landscape") assert(metrics.actionBar.bottom <= metrics.innerHeight, `${scenario.name}: action bar is below the usable viewport`);
  if (scenario.mobile) for (const action of metrics.actions) assert(action.height >= 44 && action.width >= 44, `${scenario.name}: ${action.name} touch target is below 44px`);

  await evaluate(`(() => { const title = document.querySelector('.question-block h1'); const detail = document.querySelector('.advice-card details p'); if (title) title.textContent = '这是一段用于验证超长面试问题在狭窄屏幕与放大场景中仍然能够自然换行且不会制造横向滚动的完全合成文本'.repeat(3); if (detail) detail.textContent = '用于验证长答案布局的合成内容。'.repeat(60); })()`);
  const longTextWidth = await evaluate(`document.documentElement.scrollWidth`);
  assert(longTextWidth <= scenario.width + 1, `${scenario.name}: long content causes horizontal overflow`);

  const screenshot = await command("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  await writeFile(join(artifacts, `${scenario.name}.png`), Buffer.from(screenshot.data, "base64"));
  results.push({ ...scenario, ...metrics, longTextWidth });
}

await command("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
await evaluate(`history.pushState({}, '', '/app/interviews/demo/live'); dispatchEvent(new PopStateEvent('popstate'))`); await pause(250);
const splitBefore = await evaluate(`(() => { const separator = document.querySelector('.workspace-divider'); if (!separator) return null; separator.focus(); return { before: Number(separator.getAttribute('aria-valuenow')), focused: document.activeElement === separator }; })()`);
await evaluate(`document.querySelector('.workspace-divider').dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', code: 'ArrowRight', bubbles: true }))`); await pause(80);
const splitAfter = await evaluate(`Number(document.querySelector('.workspace-divider')?.getAttribute('aria-valuenow'))`);
await evaluate(`document.querySelector('.workspace-divider').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true }))`); await pause(80);
const splitReset = await evaluate(`Number(document.querySelector('.workspace-divider')?.getAttribute('aria-valuenow'))`);
const dividerDrag = await evaluate(`(() => { const separator = document.querySelector('.workspace-divider').getBoundingClientRect(); const workspace = document.querySelector('.focused-live-grid').getBoundingClientRect(); return { x: separator.left + separator.width / 2, y: separator.top + separator.height / 2, targetX: workspace.left + workspace.width * .55 }; })()`);
await command("Input.dispatchMouseEvent", { type: "mousePressed", x: dividerDrag.x, y: dividerDrag.y, button: "left", buttons: 1, clickCount: 1 });
await command("Input.dispatchMouseEvent", { type: "mouseMoved", x: dividerDrag.targetX, y: dividerDrag.y, button: "left", buttons: 1 });
await command("Input.dispatchMouseEvent", { type: "mouseReleased", x: dividerDrag.targetX, y: dividerDrag.y, button: "left", buttons: 0, clickCount: 1 }); await pause(100);
const pointerAfter = await evaluate(`Number(document.querySelector('.workspace-divider')?.getAttribute('aria-valuenow'))`);
await evaluate(`document.querySelector('.workspace-divider').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true }))`); await pause(80);
const splitReview = splitBefore && { ...splitBefore, after: splitAfter, reset: splitReset, pointerAfter };
assert(splitReview?.focused && splitReview.after > splitReview.before && splitReview.reset === 42 && splitReview.pointerAfter > 42, `desktop: split interaction failed ${JSON.stringify(splitReview)}`);

await evaluate(`(() => { const input = document.querySelector('.compact-question-bar textarea'); const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set; setter.call(input, '浏览器检查用合成问题'); input.dispatchEvent(new Event('input', { bubbles: true })); })()`); await pause(80);
await evaluate(`document.querySelector('.compact-question-bar button[aria-label="回答问题"]').click()`); await pause(120);
const cancellationBefore = await evaluate(`({ hasStop: [...document.querySelectorAll('button')].some(node => node.textContent.trim() === '终止回答'), taskLabel: document.querySelector('.answer-task-control span')?.textContent, hasAdvice: Boolean(document.querySelector('.advice-card')) })`);
assert(cancellationBefore.hasStop && cancellationBefore.hasAdvice, `answer cancellation: active control missing ${JSON.stringify(cancellationBefore)}`);
await evaluate(`[...document.querySelectorAll('button')].find(node => node.textContent.trim() === '终止回答').click()`); await pause(180);
const cancellationAfter = await evaluate(`({ cancelled: Boolean(document.querySelector('.cancelled-answer')), hasStop: [...document.querySelectorAll('button')].some(node => node.textContent.trim() === '终止回答'), hasAdvice: Boolean(document.querySelector('.advice-card')), interviewControl: [...document.querySelectorAll('.session-bar button')].map(node => node.textContent.trim()) })`);
assert(cancellationAfter.cancelled && !cancellationAfter.hasStop && !cancellationAfter.hasAdvice, `answer cancellation: terminal UI is incorrect ${JSON.stringify(cancellationAfter)}`);

const { nodes } = await command("Accessibility.getFullAXTree");
const axNames = nodes.map(node => node.name?.value).filter(Boolean);
for (const name of ["实时对话", "回答", "手动输入面试官的问题", "回答问题", "截图回答", "调整实时对话与回答宽度"]) assert(axNames.includes(name), `accessibility tree missing: ${name}`);

await command("Emulation.setDeviceMetricsOverride", { width: 390, height: 420, deviceScaleFactor: 2, mobile: true });
const keyboardReview = await evaluate(`(() => { const input = document.querySelector('.compact-question-bar textarea'); input.focus(); input.scrollIntoView({ block: 'center' }); const bar = document.querySelector('.compact-question-bar').getBoundingClientRect(); const buttons = [...document.querySelectorAll('.compact-question-bar button')].map(node => node.getBoundingClientRect()).map(rect => ({ top: rect.top, bottom: rect.bottom })); return { focused: document.activeElement === input, barTop: bar.top, barBottom: bar.bottom, buttons }; })()`);
assert(keyboardReview.focused, "soft-keyboard review: input could not receive focus");
assert(keyboardReview.buttons.every(button => button.top >= 0 && button.bottom <= 420), `soft-keyboard review: actions cannot be scrolled into the reduced viewport ${JSON.stringify(keyboardReview)}`);

for (const viewport of [{ name: "phone", width: 390, height: 844 }, { name: "tablet", width: 820, height: 1180 }, { name: "desktop", width: 1440, height: 900 }]) {
  await command("Emulation.setDeviceMetricsOverride", { width: viewport.width, height: viewport.height, deviceScaleFactor: viewport.width < 1000 ? 2 : 1, mobile: viewport.width < 1000 });
  await evaluate(`history.pushState({}, '', '/app/library'); dispatchEvent(new PopStateEvent('popstate'))`); await pause(250);
  const library = await evaluate(`({ width: document.documentElement.scrollWidth, heading: document.querySelector('h1')?.textContent, hasFormula: document.body.textContent.includes('每 1,000 Token 20 点'), hasAdd: [...document.querySelectorAll('button')].some(node => node.textContent.includes('添加资料')) })`);
  assert(library.width <= viewport.width + 1, `library ${viewport.name}: horizontal overflow`); assert(library.hasFormula && library.hasAdd, `library ${viewport.name}: quote entry missing`); commercialResults.push({ page: "library", ...viewport, ...library });
}
const redemptionResults = [];
for (const viewport of [{ name: "phone", width: 390, height: 844 }, { name: "tablet", width: 820, height: 1180 }, { name: "desktop", width: 1440, height: 900 }]) {
  await command("Emulation.setDeviceMetricsOverride", { width: viewport.width, height: viewport.height, deviceScaleFactor: viewport.width < 1000 ? 2 : 1, mobile: viewport.width < 1000 });
  await evaluate(`history.pushState({}, '', '/app/library'); dispatchEvent(new PopStateEvent('popstate'))`); await pause(60);
  await evaluate(`history.pushState({}, '', '/app/billing'); dispatchEvent(new PopStateEvent('popstate'))`); await pause(180);
  const before = await evaluate(`(() => { const input = document.querySelector('#points-redemption-code'); const button = [...document.querySelectorAll('.redemption-card button')].find(node => node.textContent.includes('立即兑换')); return { width: document.documentElement.scrollWidth, inputLabel: document.querySelector('label[for="points-redemption-code"]')?.textContent, buttonHeight: button?.getBoundingClientRect().height, inputHeight: input?.getBoundingClientRect().height, hasCheckout: Boolean(document.querySelector('[role=dialog]')), disabled: button?.disabled }; })()`);
  assert(before.width <= viewport.width + 1 && before.inputLabel === "积分兑换码" && !before.hasCheckout && before.disabled, `redemption ${viewport.name}: initial state is invalid ${JSON.stringify(before)}`);
  assert(before.buttonHeight >= 44 && before.inputHeight >= 44, `redemption ${viewport.name}: touch targets are below 44px`);
  await evaluate(`(() => { const input = document.querySelector('#points-redemption-code'); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, 'SYNTHETIC-DEMO'); input.dispatchEvent(new Event('input', { bubbles: true })); input.closest('form').requestSubmit(); })()`); await pause(180);
  const redeemed = await evaluate(`({ status: document.querySelector('#redemption-status')?.textContent, balance: document.querySelector('.balance-card strong')?.textContent, credit: [...document.querySelectorAll('.points-history article')].some(node => node.textContent.includes('+120 点')), inputCleared: document.querySelector('#points-redemption-code')?.value === '' })`);
  assert(/兑换成功|已兑换至当前账号/.test(redeemed.status) && redeemed.balance === "320 点" && redeemed.credit && redeemed.inputCleared, `redemption ${viewport.name}: success/replay state failed ${JSON.stringify(redeemed)}`);
  await evaluate(`(() => { const input = document.querySelector('#points-redemption-code'); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, 'SYNTHETIC-MISSING'); input.dispatchEvent(new Event('input', { bubbles: true })); input.closest('form').requestSubmit(); })()`); await pause(140);
  const unavailable = await evaluate(`document.querySelector('#redemption-status')?.textContent`); assert(unavailable.includes("兑换码不可用"), `redemption ${viewport.name}: safe unavailable state missing`);
  redemptionResults.push({ ...viewport, before, redeemed, unavailable });
  const shot = await command("Page.captureScreenshot", { format: "png", captureBeyondViewport: false }); await writeFile(join(artifacts, `redemption-${viewport.name}.png`), Buffer.from(shot.data, "base64"));
}
await command("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
await evaluate(`history.pushState({}, '', '/app/billing'); dispatchEvent(new PopStateEvent('popstate'))`); await pause(100);
await evaluate(`[...document.querySelectorAll('.price-card button')][0].click()`); await pause(80);
const checkoutRegression = await evaluate(`({ dialog: Boolean(document.querySelector('[role=dialog]')), hasTransactionInput: Boolean(document.querySelector('[aria-label="交易单号"]')), redemptionOutsideDialog: !document.querySelector('[role=dialog]')?.textContent.includes('积分兑换码') })`);
assert(checkoutRegression.dialog && !checkoutRegression.hasTransactionInput && checkoutRegression.redemptionOutsideDialog, `checkout regression: ${JSON.stringify(checkoutRegression)}`);
await evaluate(`document.querySelector('.sheet-close').click()`);
await command("Page.navigate", { url: `${baseUrl}/app/settings` }); await pause(250);
const settings = await evaluate(`({ hasRetentionSelect: Boolean(document.querySelector('[aria-label="面试记录保存期限"]')), hasAudioDefault: document.body.textContent.includes('默认不保存'), hasDataGuide: [...document.querySelectorAll('a')].some(node => node.textContent.includes('查看数据说明')) })`);
assert(!settings.hasRetentionSelect && settings.hasAudioDefault && settings.hasDataGuide, `settings: data controls are not truthful ${JSON.stringify(settings)}`);
const report = { baseUrl, artifacts, continuation, scenarios: results, commercialResults, redemptionResults, checkoutRegression, splitReview, cancellationBefore, cancellationAfter, settings, accessibilityNamesChecked: axNames.filter(name => ["实时对话", "回答", "手动输入面试官的问题", "回答问题", "截图回答", "调整实时对话与回答宽度"].includes(name)), keyboardReview };
await writeFile(join(artifacts, "report.json"), JSON.stringify(report, null, 2));
process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
browserSocket.close();
stopBrowser();
