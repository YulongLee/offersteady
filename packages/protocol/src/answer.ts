import type { AnswerProvenance } from "./context.js";

export type AnswerTaskStatus = "queued" | "generating" | "completed" | "failed" | "cancelled";

export interface AnswerTaskSnapshot {
  readonly id: string;
  readonly interviewId: string;
  readonly userId: string;
  readonly billingUsageId: string;
  readonly questionId: string;
  readonly revision: number;
  readonly status: AnswerTaskStatus;
  readonly question: string;
  readonly partialText?: string;
  readonly completedText?: string;
  readonly provenance?: AnswerProvenance;
  readonly materialContextStatus?: "not-assembled" | "ready" | "degraded" | "no-context" | string;
  readonly updatedAtMs: number;
}

export interface CancelAnswerCommand {
  readonly interviewId: string;
  readonly answerTaskId: string;
  readonly expectedRevision: number;
  readonly idempotencyKey: string;
}

export type CancelAnswerOutcome = "cancelled" | "already-cancelled" | "not-cancellable" | "stale-revision";

export interface CancelAnswerResult {
  readonly outcome: CancelAnswerOutcome;
  readonly task: AnswerTaskSnapshot;
  readonly billingReleased: boolean;
}

export const isActiveAnswerStatus = (status: AnswerTaskStatus): boolean => status === "queued" || status === "generating";

export const canTransitionAnswerTask = (from: AnswerTaskStatus, to: AnswerTaskStatus): boolean => {
  if (from === to) return true;
  if (from === "queued") return to === "generating" || to === "completed" || to === "failed" || to === "cancelled";
  if (from === "generating") return to === "completed" || to === "failed" || to === "cancelled";
  return false;
};
