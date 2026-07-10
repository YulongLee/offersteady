import type { AnswerTaskSnapshot, AnswerTaskStatus, CancelAnswerCommand, CancelAnswerResult } from "@offersteady/protocol";
import { canTransitionAnswerTask, isActiveAnswerStatus } from "@offersteady/protocol";
import type { BillingService } from "./billing-service.js";

export interface AnswerGenerationAdapter {
  abort(answerTaskId: string): Promise<void> | void;
}

export class AnswerTaskError extends Error {
  constructor(readonly code: "not-found" | "forbidden" | "invalid-state", message: string) { super(message); }
}

export class AnswerTaskCoordinator {
  private readonly tasks = new Map<string, AnswerTaskSnapshot>();
  private readonly cancelResults = new Map<string, CancelAnswerResult>();

  constructor(private readonly billing: BillingService, private readonly generation: AnswerGenerationAdapter) {}

  create(input: Omit<AnswerTaskSnapshot, "revision" | "status" | "updatedAtMs">, nowMs = Date.now()): AnswerTaskSnapshot {
    const existing = this.tasks.get(input.id);
    if (existing) return existing;
    const task: AnswerTaskSnapshot = { ...input, revision: 1, status: "queued", updatedAtMs: nowMs };
    this.tasks.set(task.id, task);
    return task;
  }

  get(answerTaskId: string): AnswerTaskSnapshot {
    const task = this.tasks.get(answerTaskId);
    if (!task) throw new AnswerTaskError("not-found", "回答任务不存在");
    return task;
  }

  transition(answerTaskId: string, expectedRevision: number, status: AnswerTaskStatus, nowMs = Date.now(), completedText?: string): AnswerTaskSnapshot {
    const task = this.get(answerTaskId);
    if (task.revision !== expectedRevision || !canTransitionAnswerTask(task.status, status)) throw new AnswerTaskError("invalid-state", "回答任务状态已变化");
    const next: AnswerTaskSnapshot = status === "completed" && completedText
      ? (() => { const { partialText: _partialText, ...base } = task; return { ...base, status, completedText, revision: task.revision + 1, updatedAtMs: nowMs }; })()
      : { ...task, status, revision: task.revision + 1, updatedAtMs: nowMs };
    this.tasks.set(answerTaskId, next);
    if (status === "completed") this.billing.settleUsage(task.billingUsageId, nowMs);
    if (status === "failed") this.billing.releaseUsage(task.billingUsageId, nowMs);
    return next;
  }

  appendChunk(answerTaskId: string, expectedRevision: number, chunk: string, nowMs = Date.now()): AnswerTaskSnapshot {
    const task = this.get(answerTaskId);
    if (task.revision !== expectedRevision || !isActiveAnswerStatus(task.status)) return task;
    const next: AnswerTaskSnapshot = { ...task, status: "generating", partialText: `${task.partialText ?? ""}${chunk}`, revision: task.revision + 1, updatedAtMs: nowMs };
    this.tasks.set(answerTaskId, next);
    return next;
  }

  async cancel(userId: string, command: CancelAnswerCommand, nowMs = Date.now()): Promise<CancelAnswerResult> {
    const replay = this.cancelResults.get(command.idempotencyKey);
    if (replay) return replay;
    const task = this.get(command.answerTaskId);
    if (task.userId !== userId || task.interviewId !== command.interviewId) throw new AnswerTaskError("forbidden", "无权终止该回答");
    if (task.status === "cancelled") {
      const result: CancelAnswerResult = { outcome: "already-cancelled", task, billingReleased: true };
      this.cancelResults.set(command.idempotencyKey, result);
      return result;
    }
    if (task.revision !== command.expectedRevision) {
      const result: CancelAnswerResult = { outcome: "stale-revision", task, billingReleased: false };
      this.cancelResults.set(command.idempotencyKey, result);
      return result;
    }
    if (!isActiveAnswerStatus(task.status)) {
      const result: CancelAnswerResult = { outcome: "not-cancellable", task, billingReleased: false };
      this.cancelResults.set(command.idempotencyKey, result);
      return result;
    }
    const { partialText: _partialText, ...base } = task;
    const cancelled: AnswerTaskSnapshot = { ...base, status: "cancelled", revision: task.revision + 1, updatedAtMs: nowMs };
    this.tasks.set(task.id, cancelled);
    this.billing.releaseUsage(task.billingUsageId, nowMs);
    try { await this.generation.abort(task.id); } catch { /* Authoritative cancellation still wins; provider failure is operational telemetry. */ }
    const result: CancelAnswerResult = { outcome: "cancelled", task: cancelled, billingReleased: true };
    this.cancelResults.set(command.idempotencyKey, result);
    return result;
  }

  clearSession(interviewId: string) {
    for (const [id, task] of this.tasks) if (task.interviewId === interviewId) this.tasks.delete(id);
  }
}
