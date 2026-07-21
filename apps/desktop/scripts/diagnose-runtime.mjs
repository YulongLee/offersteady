import { mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const apiBaseUrl = (process.env.OFFERSTEADY_API_BASE_URL || "http://127.0.0.1:8000/api/v1").replace(/\/+$/, "");
const manualCode = process.env.OFFERSTEADY_MANUAL_CODE || "";
const deviceId = process.env.OFFERSTEADY_DEVICE_ID || "";
const sessionId = process.env.OFFERSTEADY_SESSION_ID || "";
const userId = process.env.OFFERSTEADY_USER_ID || "prototype-user";
const screenshotRequestId = process.env.OFFERSTEADY_SCREENSHOT_REQUEST_ID || "";
const runPcmProbe = process.env.OFFERSTEADY_RUN_PCM_PROBE === "1";
const waitForRealFramesMs = Number(process.env.OFFERSTEADY_WAIT_FOR_REAL_FRAMES_MS || "0");
const nativeRuntimePath = process.env.OFFERSTEADY_NATIVE_RUNTIME_PATH || path.join(root, "apps", "desktop", "native", "macos-capture", "build", "OfferSteadyCaptureRuntime");

const redactUrl = (url) => {
  try {
    const parsed = new URL(url);
    parsed.username = "";
    parsed.password = "";
    return parsed.toString();
  } catch {
    return url;
  }
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const check = async (name, run) => {
  const startedAtMs = Date.now();
  try {
    const data = await run();
    return { name, ok: !data?.failed && data?.ok !== false, durationMs: Date.now() - startedAtMs, data };
  } catch (error) {
    return {
      name,
      ok: false,
      durationMs: Date.now() - startedAtMs,
      error: error instanceof Error ? error.message : String(error),
    };
  }
};

const request = async (url, init) => {
  const response = await fetch(url, init);
  const text = await response.text();
  let payload = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = { raw: text.slice(0, 240) };
  }
  if (!response.ok) {
    throw new Error(payload?.error?.message || payload?.detail || `HTTP ${response.status}`);
  }
  return payload?.data ?? payload;
};

const sourceReceiptSummary = (item) => ({
  sourceKind: item.sourceKind,
  sourceId: item.sourceId,
  frameCount: item.frameCount,
  lastSequence: item.lastSequence,
  lastAsrStatus: item.lastAsrStatus,
  lastErrorCode: item.lastErrorCode,
});

const sourceHealthSummary = (item) => ({
  sourceKind: item.sourceKind,
  sourceId: item.sourceId,
  state: item.state,
  stage: item.stage,
  level: item.level,
  frameCount: item.frameCount ?? 0,
  backendFrameCount: item.backendFrameCount ?? 0,
  lastSignalAtMs: item.lastSignalAtMs ?? null,
  lastFrameAtMs: item.lastFrameAtMs ?? null,
  lastBackendFrameAtMs: item.lastBackendFrameAtMs ?? null,
  errorCode: item.errorCode ?? null,
  providerConnectionState: item.providerConnectionState ?? null,
  providerErrorCode: item.providerErrorCode ?? null,
});

const summarizeRuntime = (runtime) => ({
  sessionId: runtime?.sessionId,
  sessionStatus: runtime?.sessionStatus,
  stage: runtime?.stage,
  deviceRegistered: runtime?.deviceRegistered,
  machineCodeBound: runtime?.machineCodeBound,
  sessionLive: runtime?.sessionLive,
  publisherCount: runtime?.publishers?.length ?? 0,
  publishers: (runtime?.publishers ?? []).map((item) => ({
    publisherId: item.publisherId,
    sessionId: item.sessionId,
    sourceKind: item.sourceKind,
    status: item.status,
    connectedAtMs: item.connectedAtMs ?? null,
    disconnectedAtMs: item.disconnectedAtMs ?? null,
    expiresAtMs: item.expiresAtMs ?? null,
  })),
  transcriptCount: runtime?.transcriptCount,
  questionCandidateCount: runtime?.questionCandidateCount,
  lastErrorCode: runtime?.lastErrorCode,
  dominantBottleneck: runtime?.dominantBottleneck,
  anomalyReasons: runtime?.anomalyReasons ?? [],
  sourceHealth: (runtime?.sourceHealth ?? []).map(sourceHealthSummary),
  frameReceipts: (runtime?.frameReceipts ?? []).map(sourceReceiptSummary),
  performance: runtime?.performance ?? null,
});

const generateProbePcmBase64 = () => {
  const sampleRate = 16_000;
  const durationSeconds = 1.2;
  const samples = Math.floor(sampleRate * durationSeconds);
  const bytes = Buffer.alloc(samples * 2);
  for (let index = 0; index < samples; index += 1) {
    const envelope = Math.min(1, index / 1200, (samples - index) / 1200);
    const value = Math.round(Math.sin((2 * Math.PI * 440 * index) / sampleRate) * 0x2fff * envelope);
    bytes.writeInt16LE(value, index * 2);
  }
  return bytes.toString("base64");
};

const runtimeUrl = () => `${apiBaseUrl}/realtime-speech/sessions/${encodeURIComponent(sessionId)}/runtime?${new URLSearchParams({ userId }).toString()}`;

const fetchRuntime = async () => summarizeRuntime(await request(runtimeUrl()));

const classifyBackendPcmProbe = (receipt, runtime) => {
  if (!receipt) return { accepted: false, transcriptStatus: "no-receipt", providerTimeout: false, suppressedFiller: false };
  const reasons = runtime?.anomalyReasons ?? [];
  return {
    accepted: receipt.lastAsrStatus === "accepted",
    transcriptStatus: (runtime?.transcriptCount ?? 0) > 0 ? "transcript-emitted" : "accepted-no-transcript",
    providerTimeout: reasons.some((reason) => String(reason).includes("provider_partial_timeout") || String(reason).includes("provider_final_timeout")),
    suppressedFiller: reasons.some((reason) => String(reason).includes("filler_transcript_suppressed")),
    lastErrorCode: runtime?.lastErrorCode ?? null,
  };
};

const runBackendPcmProbe = async () => {
  if (!sessionId) return { skipped: true, reason: "Set OFFERSTEADY_SESSION_ID to run PCM probe." };
  const publisher = await request(`${apiBaseUrl}/realtime-speech/publishers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      userId,
      sessionId,
      sourceKind: "microphone",
      clientName: "desktop-diagnostic-pcm-probe",
    }),
  });
  const now = Date.now();
  const sourceId = "diagnostic-pcm-probe";
  await request(`${apiBaseUrl}/realtime-speech/frames`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      type: "audio-frame",
      token: publisher.token,
      deviceId: deviceId || "diagnostic-device",
      sourceId,
      sequence: 1,
      sourceKind: "microphone",
      segmentId: `diagnostic-${now}`,
      revision: 1,
      capturedAtMs: now - 1200,
      startedAtMs: now - 1200,
      endedAtMs: now,
      durationMs: 1200,
      codec: "pcm-s16le",
      sampleRateHz: 16000,
      channels: 1,
      isFinal: true,
      traceId: `diagnostic:${now}`,
      sentAtMs: now,
      audioBase64: generateProbePcmBase64(),
    }),
  });
  let latest = null;
  for (let attempt = 0; attempt < 8; attempt += 1) {
    await sleep(1500);
    latest = await fetchRuntime();
    const receipt = latest.frameReceipts.find((item) => item.sourceId === sourceId);
    if (receipt && receipt.lastAsrStatus !== "pending") {
      return {
        sourceId,
        receipt,
        classification: classifyBackendPcmProbe(receipt, latest),
        runtime: latest,
        result: receipt.lastAsrStatus === "accepted" ? "accepted" : "failed-surfaced",
      };
    }
  }
  return { sourceId, runtime: latest, classification: classifyBackendPcmProbe(null, latest), result: "pending-timeout", failed: true };
};

const realFrameEvidence = (runtime) => {
  const receipts = runtime.frameReceipts.filter((item) => item.sourceId !== "diagnostic-pcm-probe" && (item.frameCount ?? 0) > 0);
  const localFrames = runtime.sourceHealth.filter((item) => (item.frameCount ?? 0) > 0 || (item.backendFrameCount ?? 0) > 0);
  const localSignal = runtime.sourceHealth.filter((item) => (item.level ?? 0) > 0 || item.lastSignalAtMs);
  return {
    hasRealFrameReceipts: receipts.length > 0,
    receipts,
    localFrames,
    localSignal,
    blockedBeforeAsr: receipts.length === 0,
    reason: receipts.length > 0 ? "real-desktop-frames-present" : "real-desktop-capture-produced-zero-backend-frames",
  };
};

const runRealDesktopCaptureProbe = async () => {
  if (!sessionId) return { skipped: true, reason: "Set OFFERSTEADY_SESSION_ID to check real desktop capture." };
  let latest = await fetchRuntime();
  const deadline = Date.now() + Math.max(0, waitForRealFramesMs);
  while (!realFrameEvidence(latest).hasRealFrameReceipts && Date.now() < deadline) {
    await sleep(1000);
    latest = await fetchRuntime();
  }
  const evidence = realFrameEvidence(latest);
  return {
    ...evidence,
    runtime: latest,
    failed: !evidence.hasRealFrameReceipts,
  };
};

const runNativeRuntime = (command, durationMs = 1200) => {
  if (process.platform !== "darwin") return { skipped: true, reason: "Native macOS runtime probes only run on macOS." };
  if (!existsSync(nativeRuntimePath)) return { skipped: true, reason: `Native runtime not found at ${nativeRuntimePath}. Run npm run build:native -w @offersteady/desktop.` };
  const result = spawnSync(nativeRuntimePath, command ? [command, String(durationMs)] : [], { encoding: "utf8" });
  const output = (result.stdout || "").trim();
  let data = null;
  try {
    data = output ? JSON.parse(output) : null;
  } catch {
    data = { raw: output.slice(0, 240) };
  }
  if (result.status !== 0) {
    return { failed: true, exitCode: result.status, stderr: (result.stderr || "").slice(0, 400), data };
  }
  return data;
};

const runScreenshotStageProbe = async () => {
  if (screenshotRequestId) {
    const query = new URLSearchParams({ userId });
    const current = await request(`${apiBaseUrl}/screenshot-answer/capture-requests/${encodeURIComponent(screenshotRequestId)}?${query.toString()}`);
    return {
      requestId: current.requestId,
      sessionId: current.sessionId,
      status: current.status,
      answerTaskId: current.answerTaskId ?? null,
      errorMessage: current.errorMessage ?? null,
      capturedFilename: current.capturedFilename ?? null,
      claimedAtMs: current.claimedAtMs ?? null,
      completedAtMs: current.completedAtMs ?? null,
      answerTaskStatus: current.answerTask?.status ?? null,
      answerTaskErrorCode: current.answerTask?.errorCode ?? null,
      answerTaskErrorMessage: current.answerTask?.errorMessage ?? null,
    };
  }
  if (!deviceId || !manualCode) return { skipped: true, reason: "Set OFFERSTEADY_SCREENSHOT_REQUEST_ID or both OFFERSTEADY_DEVICE_ID and OFFERSTEADY_MANUAL_CODE." };
  const query = new URLSearchParams({ manualCode });
  const next = await request(`${apiBaseUrl}/screenshot-answer/desktop-devices/${encodeURIComponent(deviceId)}/capture-requests/next?${query.toString()}`);
  if (!next) return { pendingRequest: null, status: "no-pending-request" };
  return {
    requestId: next.requestId,
    sessionId: next.sessionId,
    status: next.status,
    answerTaskId: next.answerTaskId ?? null,
    errorMessage: next.errorMessage ?? null,
    claimedAtMs: next.claimedAtMs ?? null,
    completedAtMs: next.completedAtMs ?? null,
  };
};

const checks = [
  check("native.status", async () => runNativeRuntime("status")),
  check("native.microphoneProbe", async () => runNativeRuntime("probe-microphone", 1200)),
  check("native.systemProbe", async () => runNativeRuntime("probe-system", 1200)),
  check("backend.status", () => request(`${apiBaseUrl}/realtime-speech/status`)),
  check("desktop.pairingStatus", async () => {
    if (!manualCode) return { skipped: true, reason: "Set OFFERSTEADY_MANUAL_CODE to check pairing." };
    const query = new URLSearchParams({ manualCode });
    if (deviceId) query.set("deviceId", deviceId);
    return request(`${apiBaseUrl}/realtime-speech/desktop-devices/pairing-status?${query.toString()}`);
  }),
  check("session.runtime", async () => {
    if (!sessionId) return { skipped: true, reason: "Set OFFERSTEADY_SESSION_ID to check live runtime." };
    return fetchRuntime();
  }),
  check("session.transcripts", async () => {
    if (!sessionId) return { skipped: true, reason: "Set OFFERSTEADY_SESSION_ID to check transcripts." };
    const query = new URLSearchParams({ userId });
    const data = await request(`${apiBaseUrl}/realtime-speech/sessions/${encodeURIComponent(sessionId)}/transcripts?${query.toString()}`);
    return {
      sessionId: data.sessionId,
      transcriptCount: data.transcripts?.length ?? 0,
      transcripts: (data.transcripts ?? []).map((item) => ({
        segmentId: item.segmentId,
        role: item.role,
        sourceKind: item.sourceKind,
        textLength: item.text?.length ?? 0,
        isFinal: item.isFinal,
        confidence: item.confidence ?? null,
      })),
    };
  }),
  check("desktop.realCaptureProbe", runRealDesktopCaptureProbe),
  check("session.backendPcmProbe", async () => {
    if (!runPcmProbe) return { skipped: true, reason: "Set OFFERSTEADY_RUN_PCM_PROBE=1 to send a synthetic PCM probe." };
    return runBackendPcmProbe();
  }),
  check("screenshot.remoteStage", runScreenshotStageProbe),
];

const checksResult = await Promise.all(checks);
const runtimeCheck = checksResult.find((item) => item.name === "session.runtime");
const realCaptureCheck = checksResult.find((item) => item.name === "desktop.realCaptureProbe");
const pcmCheck = checksResult.find((item) => item.name === "session.backendPcmProbe");
const screenshotCheck = checksResult.find((item) => item.name === "screenshot.remoteStage");

const conclusion = {
  backendReachable: checksResult.find((item) => item.name === "backend.status")?.ok ?? false,
  pairingChecked: checksResult.find((item) => item.name === "desktop.pairingStatus")?.ok ?? false,
  runtimeStage: runtimeCheck?.data?.stage ?? null,
  realDesktopFramesPresent: Boolean(realCaptureCheck?.data?.hasRealFrameReceipts),
  backendAsrProbe: pcmCheck?.data?.classification ?? null,
  screenshotStage: screenshotCheck?.data?.status ?? null,
  likelyBlocker: realCaptureCheck?.data?.hasRealFrameReceipts
    ? (runtimeCheck?.data?.transcriptCount > 0 ? "none" : "asr-or-web-transcript")
    : "desktop-real-capture-no-frames",
};

const report = {
  generatedAt: new Date().toISOString(),
  apiBaseUrl: redactUrl(apiBaseUrl),
  privacy: {
    rawAudioPersisted: false,
    screenshotImagePersistedInDiagnostic: false,
    persistedFields: ["counts", "timings", "request ids", "source ids", "dimensions if provided", "error codes", "text lengths"],
  },
  inputs: {
    manualCode: manualCode ? "provided" : "missing",
    deviceId: deviceId ? "provided" : "missing",
    sessionId: sessionId ? "provided" : "missing",
    userId: userId ? "provided" : "missing",
    screenshotRequestId: screenshotRequestId ? "provided" : "missing",
    pcmProbe: runPcmProbe ? "enabled" : "disabled",
    waitForRealFramesMs,
    nativeRuntimePath: nativeRuntimePath ? "configured" : "missing",
  },
  conclusion,
  checks: checksResult,
};

const outputDir = path.join(root, "artifacts", "desktop-runtime-diagnostics");
await mkdir(outputDir, { recursive: true });
const outputPath = path.join(outputDir, `diagnostic-${Date.now()}.json`);
await writeFile(outputPath, JSON.stringify(report, null, 2), "utf-8");
console.log(`Desktop runtime diagnostic written: ${outputPath}`);
console.log(`Likely blocker: ${conclusion.likelyBlocker}`);
const failed = report.checks.filter((item) => !item.ok && !item.data?.skipped);
if (failed.length) {
  console.error(`Failed checks: ${failed.map((item) => item.name).join(", ")}`);
  process.exitCode = 1;
}
