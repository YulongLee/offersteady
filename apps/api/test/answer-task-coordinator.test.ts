import { describe, expect, it, vi } from "vitest";
import { AnswerTaskCoordinator, AnswerTaskError } from "../src/answer-task-coordinator.js";
import { BillingService } from "../src/billing-service.js";

const setup = (withPass = false) => {
  const billing = new BillingService();
  billing.grantWelcome("user-1", true, 1);
  if (withPass) billing.activateVerifiedProduct("user-1", { id: "pass", catalogVersion: 3, kind: "time_pass", displayName: "3 天会员", priceCents: 6990, durationDays: 3, knowledgeIndexAllowance: 0, published: true }, "order-pass", 2);
  const abort = vi.fn(async () => undefined);
  const coordinator = new AnswerTaskCoordinator(billing, { abort });
  billing.reserveUsage("user-1", "usage-1", "answer", 3);
  const task = coordinator.create({ id: "answer-1", interviewId: "interview-1", userId: "user-1", billingUsageId: "usage-1", questionId: "question-1", question: "synthetic interview question" }, 4);
  return { billing, coordinator, abort, task };
};

describe("answer task coordinator", () => {
  it("cancels once, releases points and ignores repeated commands", async () => {
    const { billing, coordinator, abort, task } = setup();
    expect(billing.balance("user-1")).toBe(195);
    const command = { interviewId: "interview-1", answerTaskId: task.id, expectedRevision: task.revision, idempotencyKey: "cancel-1" };
    const first = await coordinator.cancel("user-1", command, 5);
    const replay = await coordinator.cancel("user-1", command, 6);
    expect(first.outcome).toBe("cancelled");
    expect(replay).toEqual(first);
    expect(billing.balance("user-1")).toBe(200);
    expect(abort).toHaveBeenCalledOnce();
  });

  it("rejects cross-user and cross-interview cancellation", async () => {
    const { coordinator, task } = setup();
    await expect(coordinator.cancel("other", { interviewId: "interview-1", answerTaskId: task.id, expectedRevision: 1, idempotencyKey: "wrong-user" })).rejects.toMatchObject({ code: "forbidden" } satisfies Partial<AnswerTaskError>);
    await expect(coordinator.cancel("user-1", { interviewId: "other", answerTaskId: task.id, expectedRevision: 1, idempotencyKey: "wrong-session" })).rejects.toMatchObject({ code: "forbidden" } satisfies Partial<AnswerTaskError>);
  });

  it("keeps cancelled tasks final and discards late provider chunks", async () => {
    const { coordinator, task } = setup();
    const cancelled = await coordinator.cancel("user-1", { interviewId: "interview-1", answerTaskId: task.id, expectedRevision: 1, idempotencyKey: "cancel" }, 5);
    expect(coordinator.appendChunk(task.id, cancelled.task.revision, "late", 6)).toEqual(cancelled.task);
    expect(() => coordinator.transition(task.id, cancelled.task.revision, "completed", 7, "late complete")).toThrow(AnswerTaskError);
  });

  it("lets completion win an atomic race and settle only once", async () => {
    const { billing, coordinator, task } = setup();
    const completed = coordinator.transition(task.id, task.revision, "completed", 5, "synthetic completed advice");
    const result = await coordinator.cancel("user-1", { interviewId: "interview-1", answerTaskId: task.id, expectedRevision: completed.revision, idempotencyKey: "late-cancel" }, 6);
    expect(result.outcome).toBe("not-cancellable");
    expect(result.task.completedText).toBe("synthetic completed advice");
    expect(billing.balance("user-1")).toBe(195);
  });

  it("reports a stale revision without changing an active task", async () => {
    const { coordinator, task } = setup();
    const generating = coordinator.appendChunk(task.id, task.revision, "partial", 5);
    const result = await coordinator.cancel("user-1", { interviewId: "interview-1", answerTaskId: task.id, expectedRevision: task.revision, idempotencyKey: "stale" }, 6);
    expect(result.outcome).toBe("stale-revision");
    expect(result.task).toEqual(generating);
  });

  it("records cancellation without points movement for active-pass users", async () => {
    const { billing, coordinator, task } = setup(true);
    const before = billing.balance("user-1");
    const result = await coordinator.cancel("user-1", { interviewId: "interview-1", answerTaskId: task.id, expectedRevision: task.revision, idempotencyKey: "pass-cancel" }, 5);
    expect(result.outcome).toBe("cancelled");
    expect(billing.balance("user-1")).toBe(before);
  });
});
