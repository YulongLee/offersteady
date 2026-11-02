// Local synthetic preview only. This entry is absent from production Vite inputs.
import "../src/legacy-browser-polyfills";
import { Suspense, useState } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { interviewAppAdapter } from "../src/app-adapter";
import { PrototypeContext } from "../src/app-context";
import type { CollectedScreenshot, SubmitManualAnswerResult, WebAppState } from "../src/domain";
import { LivePage } from "../src/LivePage";
import { FixtureInterviewAdapter, syntheticState } from "../src/test-state";
import "../src/styles.css";

// Every adapter operation uses synthetic memory; even accidental fetches are blocked.
globalThis.fetch = async () => { throw new Error("External requests are disabled in this local preview."); };
const fixture = new FixtureInterviewAdapter();
const target = interviewAppAdapter as unknown as Record<string, (...args: never[]) => unknown>;
const methods = fixture as unknown as Record<string, (...args: never[]) => unknown>;
for (const method of Object.getOwnPropertyNames(FixtureInterviewAdapter.prototype)) {
  if (method !== "constructor" && typeof methods[method] === "function") target[method] = methods[method]!.bind(fixture);
}
const captures = new Map<string, CollectedScreenshot>();
let sequence = 0;
let currentAnswer: SubmitManualAnswerResult | null = null;
const scenario = new URLSearchParams(location.search).get("scenario");
const failureScenarios: Record<string, string> = {
  "assistant-offline": "电脑伴随程序心跳已过期，请保持伴随程序打开。",
  "binding-invalid": "网页端绑定已失效，请重新绑定机器码。",
  "capture-stage-error": "截图阶段 capture-failed 失败：synthetic capture timeout",
  "upload-stage-error": "截图阶段 upload-failed 失败：synthetic upload timeout",
};
let failureShown = false;
let singleAttempt = 0;
const failOnce = () => {
  if (!failureShown && scenario && failureScenarios[scenario]) {
    failureShown = true;
    throw new Error(failureScenarios[scenario]);
  }
};
const pause = (ms: number, signal?: AbortSignal) => new Promise<void>((resolve, reject) => {
  if (signal?.aborted) { reject(new DOMException("Aborted", "AbortError")); return; }
  const abort = () => { window.clearTimeout(timer); reject(new DOMException("Aborted", "AbortError")); };
  const timer = window.setTimeout(() => { signal?.removeEventListener("abort", abort); resolve(); }, ms);
  signal?.addEventListener("abort", abort, { once: true });
});
interviewAppAdapter.getScreenshotCapturePolicy = async () => ({ maxImagesPerTask: 4 });
interviewAppAdapter.captureScreenshot = async (_command, signal, onStage) => {
  onStage?.({ name: "合成屏幕", stage: "waiting-desktop" });
  await pause(350, signal);
  onStage?.({ name: "合成屏幕", stage: "uploading" });
  await pause(250, signal);
  failOnce();
  if (scenario === "capture-error" && sequence > 0) throw new Error("合成截屏失败，请检查助手后重试。");
  const number = ++sequence;
  const capture = { requestId: `synthetic-capture-${number}`, imageId: `synthetic-image-${number}`, name: `合成长题第 ${number} 页` };
  captures.set(capture.requestId, capture);
  return capture;
};
interviewAppAdapter.submitScreenshotAnswer = async (command, signal, onStage) => {
  const attempt = ++singleAttempt;
  onStage?.({ name: "合成屏幕", stage: "waiting-desktop" });
  if (scenario === "cancel-late-error" && attempt === 1) {
    await pause(6000); // Intentionally uncancellable: reproduces an obsolete transport callback.
    onStage?.({ name: "旧合成屏幕", stage: "failed", errorMessage: "旧截图请求已取消 (409)" });
    throw new Error("旧截图请求已取消 (409)");
  }
  await pause(450, signal);
  failOnce();
  const fixtureResult = await fixture.submitScreenshotAnswer(command, signal);
  const answerText = "这是一次合成截图回答。既有重试入口已恢复，未连接真实助手或调用模型。";
  const result: SubmitManualAnswerResult = {
    question: { ...fixtureResult.question, text: "合成笔试题目", advice: { ...fixtureResult.question.advice, detail: answerText, outline: [], sourceTypes: [], inference: "" } },
    task: { ...fixtureResult.task, question: "合成笔试题目", completedText: answerText },
  };
  currentAnswer = result;
  return result;
};
interviewAppAdapter.cancelDesktopShortcutScreenshot = async requestId => { captures.delete(requestId); };
interviewAppAdapter.loadInterviewWorkspace = async () => ({ questions: currentAnswer ? [currentAnswer.question] : [], activeAnswerTask: currentAnswer?.task ?? null });
interviewAppAdapter.submitScreenshotBatch = async (command, signal, onStage, onUpdate) => {
  if (!command.captureRequestIds.every(requestId => captures.has(requestId))) throw new Error("截图已过期，请重新截取。");
  onStage?.({ name: `${command.captureRequestIds.length} 张合成截图`, stage: "recognizing" });
  await pause(650, signal);
  if (scenario === "answer-error") throw new Error("合成连接失败");
  const count = command.captureRequestIds.length;
  const base = syntheticState.questions[0]!;
  const answerText = `已将按顺序截取的 ${count} 张画面作为一道完整题目处理。\n\n这是交互预览的合成结果，没有调用真实模型。正式使用时，这里会显示结合所有截图得到的完整回答。\n\n你可以继续截取下一道题，或关闭顶部“多屏回答”恢复原来的截屏回答。`;
  const taskId = `synthetic-batch-${sequence}`;
  const result: SubmitManualAnswerResult = {
    question: { ...base, id: taskId, text: `多屏题目 · ${count} 张截图`, input: "screenshot", status: "confirmed", advice: { ...base.advice, detail: answerText, sourceTypes: [], inference: "", provenance: { selectionRevision: 0, usedSources: [] } } },
    task: { id: taskId, interviewId: command.interviewId, userId: "admin", billingUsageId: `screenshot-answer:${taskId}`, questionId: taskId, question: `多屏题目 · ${count} 张截图`, revision: 1, status: "completed", completedText: answerText, updatedAtMs: Date.now() },
  };
  onStage?.({ name: `${count} 张合成截图`, stage: "generating" });
  onUpdate?.({ ...result, task: { ...result.task, status: "generating", partialText: "正在结合所有截图整理完整回答…" } });
  await pause(900, signal);
  currentAnswer = result;
  return result;
};
function Preview() {
  const [state, setState] = useState<WebAppState>(() => {
    const next = structuredClone(syntheticState);
    next.interviews = [{ ...next.interviews.find(item => item.id === "demo")!, title: "笔试模式", sessionMode: "written", status: "active" }];
    next.questions = []; next.activeAnswerTask = null; next.captureState = "ready";
    return next;
  });
  return <PrototypeContext.Provider value={{ state, setState, authenticated: true, setAuthenticated: () => undefined, logout: async () => undefined }}><MemoryRouter initialEntries={["/app/interviews/demo/live"]}><Suspense fallback={<p>正在打开本地预览…</p>}><Routes><Route path="/app/interviews/:id/live" element={<LivePage brand={<strong style={{ color: "var(--brand)", fontSize: 18 }}>面试稳</strong>} accountMenu={<span className="account-avatar">用户</span>} />} /><Route path="*" element={<main style={{ padding: 32 }}><h1>本地笔试已结束</h1><p>刷新此页可重新测试。预览未创建真实会话。</p></main>} /></Routes></Suspense></MemoryRouter></PrototypeContext.Provider>;
}
const previewRoot = createRoot(document.getElementById("root")!);
previewRoot.render(<Preview />);
if (import.meta.hot) import.meta.hot.dispose(() => previewRoot.unmount());
