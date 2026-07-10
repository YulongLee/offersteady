import type { StartInterviewCommand, StartInterviewResult } from "@offersteady/protocol";

export interface InterviewSessionReadiness {
  readonly ownerUserId: string;
  readonly microphoneGranted: boolean;
  readonly systemAudioGranted: boolean;
}

export class InterviewSessionError extends Error {
  constructor(readonly code: "forbidden" | "permission-required", message: string) { super(message); }
}

export class InterviewSessionService {
  private readonly results = new Map<string, StartInterviewResult>();
  private readonly activeBySession = new Map<string, StartInterviewResult>();

  start(command: StartInterviewCommand, readiness: InterviewSessionReadiness, nowMs = Date.now()): StartInterviewResult {
    const replay = this.results.get(command.idempotencyKey);
    if (replay) return replay;
    if (readiness.ownerUserId !== command.requestedByUserId) throw new InterviewSessionError("forbidden", "无权开始该面试");
    const active = this.activeBySession.get(command.sessionId);
    if (active) { this.results.set(command.idempotencyKey, active); return active; }
    if (command.inputMode === "dual-channel-audio" && (!readiness.microphoneGranted || !readiness.systemAudioGranted || command.sourceIds.length < 2)) throw new InterviewSessionError("permission-required", "双声道尚未完成授权和来源准备");
    const result: StartInterviewResult = { sessionId: command.sessionId, status: "active", captureState: command.inputMode === "manual" ? "ready" : "capturing", startedAtMs: nowMs };
    this.results.set(command.idempotencyKey, result);
    this.activeBySession.set(command.sessionId, result);
    return result;
  }
}
