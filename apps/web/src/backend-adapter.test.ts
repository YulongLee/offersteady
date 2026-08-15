import { beforeEach, describe, expect, it, vi } from "vitest";

import { BackendPreviewInterviewAdapter } from "./backend-adapter";
import { syntheticState } from "./test-state";

const envelope = (data: unknown) => ({
  success: true,
  data,
  error: null,
  requestId: "req-test",
  meta: { apiVersion: "v1", timestamp: "2026-07-01T00:00:00Z" },
});

describe("backend preview adapter", () => {
  beforeEach(() => {
    const store = new Map<string, string>();
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: {
        getItem: vi.fn((key: string) => store.get(key) ?? null),
        setItem: vi.fn((key: string, value: string) => store.set(key, value)),
        removeItem: vi.fn((key: string) => store.delete(key)),
      },
    });
  });

  it("loads app state from the backend web state API", async () => {
    const fetchImpl = vi.fn(async () => new Response(JSON.stringify(envelope(syntheticState)), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", fetchImpl as typeof fetch);
    const state = await adapter.loadState();
    expect(fetchImpl).toHaveBeenCalledWith("http://localhost:8000/api/v1/web/state", expect.any(Object));
    expect(state.interviews[0]?.id).toBe(syntheticState.interviews[0]?.id);
  });

  it("restores one authoritative interview workspace across devices", async () => {
    window.localStorage.setItem("offersteady.auth.access_token", "access-token");
    window.localStorage.setItem("offersteady.auth.refresh_token", "refresh-token");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user-1", displayName: "测试用户", createdAtMs: 1, bindings: [] }));
    const chatTask = {
      taskId: "chat-task-1", sessionId: "session-1", ownerUserId: "user-1", question: "请介绍项目难点", answerText: "先说明背景，再说明技术决策。", status: "completed", updatedAtMs: 100, chunks: [],
    };
    const screenshotTask = {
      taskId: "shot-task-1", sessionId: "session-1", ownerUserId: "user-1", instruction: "回答截图中的算法题", answerText: "使用双指针。", status: "completed", imageIds: ["image-1"], imageCount: 1, retrievalExcerptCount: 0, retryCount: 0, createdAtMs: 150, updatedAtMs: 200, chunks: [], visionSummaryTitle: "算法截图题",
    };
    const fetchImpl = vi.fn(async (input: string | URL | Request) => new Response(JSON.stringify(envelope(
      String(input).includes("/live-answer/") ? [chatTask] : [screenshotTask],
    )), { status: 200, headers: { "Content-Type": "application/json" } }));
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", fetchImpl as typeof fetch);

    const workspace = await adapter.loadInterviewWorkspace("session-1");

    expect(workspace.questions.map(question => question.id)).toEqual(["shot-task-1", "chat-task-1"]);
    expect(workspace.questions[0]).toMatchObject({ text: "算法截图题", input: "screenshot" });
    expect(workspace.activeAnswerTask?.id).toBe("shot-task-1");
    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });

  it("does not duplicate the API prefix when the configured base URL already includes it", async () => {
    const fetchImpl = vi.fn(async () => new Response(JSON.stringify(envelope(syntheticState)), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000/api/v1", fetchImpl as typeof fetch);
    await adapter.loadState();
    expect(fetchImpl).toHaveBeenCalledWith("http://localhost:8000/api/v1/web/state", expect.any(Object));
  });

  it("maps backend model-runtime failures into failed answer content", async () => {
    window.localStorage.setItem("offersteady.auth.access_token", "access-token");
    window.localStorage.setItem("offersteady.auth.refresh_token", "refresh-token");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user-1", displayName: "测试用户", createdAtMs: 1, bindings: [] }));
    const fetchImpl = vi.fn(async () => new Response(JSON.stringify(envelope({
      task: {
        taskId: "task-failed",
        sessionId: "session-1",
        ownerUserId: "user-1",
        question: "为什么模型不可用？",
        answerText: "",
        status: "failed",
        errorMessage: "当前对话模型鉴权失败，请检查服务配置。",
        updatedAtMs: 123,
        chunks: [],
      },
    })), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", fetchImpl as typeof fetch);
    const result = await adapter.submitManualAnswer({ interviewId: "session-1", question: "为什么模型不可用？", idempotencyKey: "manual:failed" });
    expect(result.question.status).toBe("failed");
    expect(result.question.advice.detail).toBe("当前对话模型鉴权失败，请检查服务配置。");
    expect(result.task.status).toBe("failed");
  });

  it("surfaces backend failures instead of falling back to fixture state", async () => {
    const fetchImpl = vi.fn(async () => { throw new Error("backend offline"); });
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", fetchImpl as typeof fetch);
    await expect(adapter.loadState()).rejects.toMatchObject({ code: "network" });
  });

  it("submits manual live questions to the backend live-answer API", async () => {
    window.localStorage.setItem("offersteady.auth.access_token", "access-token");
    window.localStorage.setItem("offersteady.auth.refresh_token", "refresh-token");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user-1", displayName: "测试用户", createdAtMs: 1, bindings: [] }));
    const fetchImpl = vi.fn(async () => new Response(JSON.stringify(envelope({
      task: {
        taskId: "task-1",
        sessionId: "session-1",
        ownerUserId: "user-1",
        question: "如何设计前端监控？",
        answerText: "先讲指标，再讲采集，最后讲告警闭环。",
        status: "completed",
        updatedAtMs: 123,
        chunks: [
          { sequence: 1, text: "先讲指标，", isFinal: false },
          { sequence: 2, text: "再讲采集。", isFinal: true },
        ],
      },
    })), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", fetchImpl as typeof fetch);
    const result = await adapter.submitManualAnswer({ interviewId: "session-1", question: "如何设计前端监控？", idempotencyKey: "manual:test" });
    expect(fetchImpl).toHaveBeenCalledWith("http://localhost:8000/api/v1/live-answer/questions", expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({ "Content-Type": "application/json" }),
      body: JSON.stringify({ userId: "user-1", sessionId: "session-1", question: "如何设计前端监控？", stream: true, idempotencyKey: "manual:test" }),
    }));
    expect(result.question).toMatchObject({ id: "task-1", text: "如何设计前端监控？", input: "manual", status: "confirmed" });
    expect(result.question.advice.detail).toBe("先讲指标，再讲采集，最后讲告警闭环。");
    expect(result.task).toMatchObject({ id: "task-1", questionId: "task-1", status: "completed", completedText: "先讲指标，再讲采集，最后讲告警闭环。" });
  });

  it("streams manual live answer events through the backend stream API", async () => {
    window.localStorage.setItem("offersteady.auth.access_token", "access-token");
    window.localStorage.setItem("offersteady.auth.refresh_token", "refresh-token");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user-1", displayName: "测试用户", createdAtMs: 1, bindings: [] }));
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        const encoder = new TextEncoder();
        controller.enqueue(encoder.encode(`event: task-started\ndata: ${JSON.stringify({
          type: "task-started",
          task: { taskId: "task-stream", sessionId: "session-1", ownerUserId: "user-1", question: "你说流式 然后怎么设计", rawQuestion: "你说流式 然后怎么设计", questionNormalizationStatus: "pending", answerText: "", status: "streaming", updatedAtMs: 1, chunks: [] },
        })}\n\n`));
        controller.enqueue(encoder.encode(`event: question-normalized\ndata: ${JSON.stringify({
          type: "question-normalized",
          task: { taskId: "task-stream", sessionId: "session-1", ownerUserId: "user-1", question: "如何设计流式回答？", rawQuestion: "你说流式 然后怎么设计", normalizedQuestion: "如何设计流式回答？", questionNormalizationStatus: "completed", answerText: "", status: "streaming", updatedAtMs: 2, chunks: [] },
        })}\n\n`));
        controller.enqueue(encoder.encode(`event: chunk\ndata: ${JSON.stringify({
          type: "chunk",
          task: { taskId: "task-stream", sessionId: "session-1", ownerUserId: "user-1", question: "如何设计流式回答？", answerText: "先展示首段。", status: "streaming", updatedAtMs: 2, chunks: [{ sequence: 1, text: "先展示首段。", isFinal: false }] },
          chunk: { sequence: 1, text: "先展示首段。", isFinal: false },
        })}\n\n`));
        controller.enqueue(encoder.encode(`event: completed\ndata: ${JSON.stringify({
          type: "completed",
          task: { taskId: "task-stream", sessionId: "session-1", ownerUserId: "user-1", question: "如何设计流式回答？", answerText: "先展示首段。再补充细节。", status: "completed", updatedAtMs: 3, chunks: [{ sequence: 1, text: "先展示首段。", isFinal: false }, { sequence: 2, text: "再补充细节。", isFinal: true }] },
        })}\n\n`));
        controller.close();
      },
    });
    const fetchImpl = vi.fn(async () => new Response(stream, {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    }));
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", fetchImpl as typeof fetch);
    const updates: string[] = [];
    const questionUpdates: string[] = [];
    const result = await adapter.submitManualAnswer(
      { interviewId: "session-1", question: "如何设计流式回答？", idempotencyKey: "manual:stream" },
      undefined,
      update => {
        updates.push(update.result.question.advice.detail);
        questionUpdates.push(update.result.question.text);
      },
    );
    expect(fetchImpl).toHaveBeenCalledWith("http://localhost:8000/api/v1/live-answer/questions/stream", expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({ Accept: "text/event-stream" }),
    }));
    expect(updates).toContain("先展示首段。");
    expect(questionUpdates).toContain("如何设计流式回答？");
    expect(result.task.status).toBe("completed");
    expect(result.question.advice.detail).toBe("先展示首段。再补充细节。");
  });

  it("keeps the browser fetch binding valid for streaming requests", async () => {
    window.localStorage.setItem("offersteady.auth.access_token", "access-token");
    window.localStorage.setItem("offersteady.auth.refresh_token", "refresh-token");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user-1", displayName: "测试用户", createdAtMs: 1, bindings: [] }));
    const originalFetch = window.fetch;
    const nativeLikeFetch = vi.fn(function (this: Window | undefined) {
      if (this !== window) throw new TypeError("Illegal invocation");
      const encoder = new TextEncoder();
      return Promise.resolve(new Response(new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(encoder.encode(`event: completed\ndata: ${JSON.stringify({
            type: "completed",
            task: { taskId: "task-bound", sessionId: "session-1", ownerUserId: "user-1", question: "验证 fetch 绑定", answerText: "绑定正常。", status: "completed", updatedAtMs: 3, chunks: [{ sequence: 1, text: "绑定正常。", isFinal: true }] },
          })}\n\n`));
          controller.close();
        },
      }), { status: 200, headers: { "Content-Type": "text/event-stream" } }));
    });
    Object.defineProperty(window, "fetch", { configurable: true, value: nativeLikeFetch });
    try {
      const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000");
      const result = await adapter.submitManualAnswer(
        { interviewId: "session-1", question: "验证 fetch 绑定", idempotencyKey: "manual:binding" },
        undefined,
        () => undefined,
      );
      expect(result.question.advice.detail).toBe("绑定正常。");
    } finally {
      Object.defineProperty(window, "fetch", { configurable: true, value: originalFetch });
    }
  });

  it("subscribes to realtime conversation snapshots through the backend stream API", async () => {
    window.localStorage.setItem("offersteady.auth.access_token", "access-token");
    window.localStorage.setItem("offersteady.auth.refresh_token", "refresh-token");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user-1", displayName: "测试用户", createdAtMs: 1, bindings: [] }));
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        const encoder = new TextEncoder();
        controller.enqueue(encoder.encode(`event: snapshot\ndata: ${JSON.stringify({
          type: "snapshot",
          transcripts: {
            sessionId: "session-1",
            transcripts: [{
              segmentId: "seg-1",
              sourceId: "system-1",
              sourceKind: "system",
              role: "interviewer",
              revision: 1,
              text: "请做个自我介绍。",
              transcriptConfidence: 0.96,
              startedAtMs: 1,
              endedAtMs: 2,
              isFinal: true,
              overlap: false,
              publishedAtMs: 3,
              performance: {
                captureToIngestMs: 12,
                queueWaitMs: 0,
                asrTtftMs: 90,
                finalTranscriptMs: 130,
                backendPushMs: 8,
              },
            }, {
              segmentId: "old-seg",
              sourceId: "system-old",
              sourceKind: "system",
              role: "interviewer",
              revision: 1,
              text: "旧 session 的问题不应出现。",
              transcriptConfidence: 0.9,
              startedAtMs: 1,
              endedAtMs: 2,
              isFinal: true,
              overlap: false,
              sessionId: "old-session"
            }],
          },
          candidates: { sessionId: "session-1", candidates: [] },
          events: { sessionId: "session-1", events: [] },
          runtime: {
            sessionId: "session-1",
            sessionStatus: "live",
            stage: "transcribing",
            backendReachable: true,
            deviceRegistered: true,
            machineCodeBound: true,
            sessionLive: true,
            manualCode: "133885",
            deviceId: "device-1",
            displayName: "面试稳伴随程序 · Mac",
            transcriptCount: 1,
            questionCandidateCount: 0,
            latestState: "connected",
            lastErrorCode: null,
            sourceHealth: [],
          },
        })}\n\n`));
        controller.close();
      },
    });
    const fetchImpl = vi.fn(async () => new Response(stream, {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    }));
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", fetchImpl as typeof fetch);
    const updates: unknown[] = [];
    await adapter.subscribeRealtimeSession("session-1", state => updates.push(state));
    expect(fetchImpl).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/realtime-speech/sessions/session-1/stream?userId=user-1&cursor=0",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({ Accept: "text/event-stream" }),
      }),
    );
    expect(updates).toHaveLength(1);
    expect(updates[0]).toMatchObject({
      speaker: {
        transcripts: [expect.objectContaining({
          text: "请做个自我介绍。",
          role: "interviewer",
          publishedAtMs: 3,
          performance: expect.objectContaining({ asrTtftMs: 90 }),
        })],
      },
    });
    expect((updates[0] as { speaker: { transcripts: readonly { text: string }[] } }).speaker.transcripts).toHaveLength(1);
    expect(JSON.stringify(updates[0])).not.toContain("旧 session 的问题不应出现");
  });

  it("preserves the realtime stream status so callers can stop invalid-session reconnect storms", async () => {
    window.localStorage.setItem("offersteady.auth.access_token", "access-token");
    window.localStorage.setItem("offersteady.auth.refresh_token", "refresh-token");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user-1", displayName: "测试用户", createdAtMs: 1, bindings: [] }));
    const fetchImpl = vi.fn(async () => new Response(JSON.stringify({ detail: "session not found" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    }));
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", fetchImpl as typeof fetch);

    await expect(adapter.subscribeRealtimeSession("missing-session", () => undefined)).rejects.toMatchObject({
      status: 404,
      message: "实时对话订阅失败（404）",
    });
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  it("maps shortcut acceptance from the existing realtime stream into immediate screenshot feedback", async () => {
    window.localStorage.setItem("offersteady.auth.access_token", "access-token");
    window.localStorage.setItem("offersteady.auth.refresh_token", "refresh-token");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user-1", displayName: "测试用户", createdAtMs: 1, bindings: [] }));
    const acceptedAtMs = Date.now();
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(`event: snapshot\ndata: ${JSON.stringify({
          type: "snapshot",
          cursor: 9,
          transcripts: { sessionId: "session-1", transcripts: [] },
          candidates: { sessionId: "session-1", candidates: [] },
          events: { sessionId: "session-1", events: [{
            eventId: "shortcut-accepted-event-1",
            kind: "screenshot-shortcut-accepted",
            payload: { requestId: "shortcut-request-1", status: "requested" },
            createdAtMs: acceptedAtMs,
          }] },
          runtime: null,
        })}\n\n`));
        controller.close();
      },
    });
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", vi.fn(async () => new Response(stream, {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    })) as typeof fetch);
    const updates: unknown[] = [];

    await adapter.subscribeRealtimeSession("session-1", update => updates.push(update));

    expect(updates).toHaveLength(1);
    expect(updates[0]).toMatchObject({
      shortcutScreenshotUpdate: {
        requestId: "shortcut-request-1",
        status: "requested",
        notificationId: "shortcut-accepted-event-1",
        acceptedAtMs,
        screenshotTask: { name: "共享屏幕截取", stage: "waiting-desktop" },
      },
    });
  });

  it("carries the active page lease through heartbeat and realtime stream requests", async () => {
    window.localStorage.setItem("offersteady.auth.access_token", "access-token");
    window.localStorage.setItem("offersteady.auth.refresh_token", "refresh-token");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user-1", displayName: "测试用户", createdAtMs: 1, bindings: [] }));
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.close();
      },
    });
    const fetchImpl = vi.fn(async (input: string | URL | Request) => {
      const url = String(input);
      if (url.includes("/web-heartbeat")) {
        return new Response(JSON.stringify(envelope({
          pageInstanceId: "page-instance-1",
          leaseGeneration: 3,
          leaseExpiresAtMs: 10_000,
        })), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      return new Response(stream, { status: 200, headers: { "Content-Type": "text/event-stream" } });
    });
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", fetchImpl as typeof fetch);

    const lease = await adapter.sendDesktopSessionHeartbeat({
      interviewId: "session-1",
      page: "live",
      pageInstanceId: "page-instance-1",
    });
    await adapter.subscribeRealtimeSession("session-1", () => undefined, undefined, {
      pageInstanceId: lease.pageInstanceId!,
      leaseGeneration: lease.leaseGeneration,
    });

    expect(fetchImpl).toHaveBeenNthCalledWith(1,
      "http://localhost:8000/api/v1/realtime-speech/sessions/session-1/web-heartbeat",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          userId: "user-1",
          bindingId: null,
          page: "live",
          pageInstanceId: "page-instance-1",
        }),
      }),
    );
    expect(fetchImpl).toHaveBeenNthCalledWith(2,
      "http://localhost:8000/api/v1/realtime-speech/sessions/session-1/stream?userId=user-1&cursor=0&pageInstanceId=page-instance-1&leaseGeneration=3",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("treats a revoked realtime stream as terminal and clears its cursor", async () => {
    window.localStorage.setItem("offersteady.auth.access_token", "access-token");
    window.localStorage.setItem("offersteady.auth.refresh_token", "refresh-token");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user-1", displayName: "测试用户", createdAtMs: 1, bindings: [] }));
    window.sessionStorage.setItem("offersteady:realtime-cursor:session-1", "27");
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode("event: revoked\ndata: {\"type\":\"revoked\",\"sessionId\":\"session-1\",\"reason\":\"session-replaced\"}\n\n"));
        controller.close();
      },
    });
    const fetchImpl = vi.fn(async () => new Response(stream, {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    }));
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", fetchImpl as typeof fetch);

    await expect(adapter.subscribeRealtimeSession("session-1", () => undefined)).rejects.toMatchObject({
      status: 410,
      message: "当前面试已被新的面试接管",
    });
    expect(window.sessionStorage.getItem("offersteady:realtime-cursor:session-1")).toBeNull();
  });

  it("starts an interview session through the backend session API", async () => {
    window.localStorage.setItem("offersteady.auth.access_token", "access-token");
    window.localStorage.setItem("offersteady.auth.refresh_token", "refresh-token");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user-1", displayName: "测试用户", createdAtMs: 1, bindings: [] }));
    const fetchImpl = vi.fn(async () => new Response(JSON.stringify(envelope({
      sessionId: "session-1",
      title: "后端启动测试",
      status: "live",
      updatedAtMs: 123,
      materialBinding: { confirmedAtMs: 123 },
    })), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", fetchImpl as typeof fetch);
    const result = await adapter.startInterviewSession("session-1");
    expect(fetchImpl).toHaveBeenCalledWith("http://localhost:8000/api/v1/sessions/session-1/start", expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({ "Content-Type": "application/json" }),
      body: JSON.stringify({ userId: "user-1" }),
    }));
    expect(result).toMatchObject({ id: "session-1", title: "后端启动测试", status: "active", readiness: 100 });
  });

  it("cancels a desktop shortcut screenshot through the remote capture API", async () => {
    window.localStorage.setItem("offersteady.auth.access_token", "access-token");
    window.localStorage.setItem("offersteady.auth.refresh_token", "refresh-token");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user-1", displayName: "测试用户", createdAtMs: 1, bindings: [] }));
    const fetchImpl = vi.fn(async () => new Response(JSON.stringify(envelope({
      requestId: "shortcut-shot-1",
      status: "cancelled",
      stage: "cancelled",
    })), { status: 200, headers: { "Content-Type": "application/json" } }));
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", fetchImpl as typeof fetch);

    await adapter.cancelDesktopShortcutScreenshot("shortcut-shot-1");

    expect(fetchImpl).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/screenshot-answer/capture-requests/shortcut-shot-1/cancel",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ userId: "user-1" }),
      }),
    );
  });

  it("persists pause and resume through the realtime capture control API", async () => {
    window.localStorage.setItem("offersteady.auth.access_token", "access-token");
    window.localStorage.setItem("offersteady.auth.refresh_token", "refresh-token");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user-1", displayName: "测试用户", createdAtMs: 1, bindings: [] }));
    const fetchImpl = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const action = JSON.parse(String(init?.body)).action;
      return new Response(JSON.stringify(envelope({ sessionId: "session-1", captureState: action === "pause" ? "paused" : "capturing" })), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", fetchImpl as typeof fetch);
    await expect(adapter.controlInterviewCapture("session-1", "pause")).resolves.toBe("paused");
    await expect(adapter.controlInterviewCapture("session-1", "resume")).resolves.toBe("capturing");
    expect(fetchImpl).toHaveBeenLastCalledWith("http://localhost:8000/api/v1/realtime-speech/sessions/session-1/capture-control", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ userId: "user-1", action: "resume" }),
    }));
  });
});
