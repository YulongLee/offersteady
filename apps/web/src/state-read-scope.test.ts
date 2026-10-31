import { describe, expect, it } from "vitest";
import { beginStateMutation, isStateAffectingRequest, stateReadGeneration } from "./state-read-scope";

describe("precise state freshness barriers", () => {
  it.each([
    ["/api/v1/documents/d", "DELETE"],
    ["/api/v1/resume/uploads/complete", "POST"],
    ["/api/v1/job-descriptions/text", "POST"],
    ["/api/v1/knowledge/collections/c/uploads/complete", "POST"],
    ["/api/v1/document-processing/tasks/t/retry", "POST"],
    ["/api/v1/sessions/s/end", "POST"],
    ["/api/v1/mock-interviews/s/start", "POST"],
    ["/api/v1/resume-optimizer/jobs/j/save-as", "POST"],
    ["/api/v1/live-answer/questions/stream", "POST"],
    ["/api/v1/screenshot-answer/sessions/s/batch-answer-requests", "POST"],
    ["/api/v1/realtime-speech/sessions/s/capture-control", "POST"],
    ["/api/v1/billing/state", "GET"],
    ["/api/v1/billing/checkout-orders/o?sync=true", "GET"],
  ])("invalidates %s %s at both boundaries", (path, method) => {
    const before = stateReadGeneration();
    const finish = beginStateMutation(path, method);
    expect(stateReadGeneration()).toBe(before + 1);
    finish(); finish();
    expect(stateReadGeneration()).toBe(before + 2);
  });

  it.each([
    ["/api/v1/web/state", "GET"],
    ["/api/v1/auth/refresh", "POST"],
    ["/api/v1/auth/sms/send-code", "POST"],
    ["/api/v1/realtime-speech/sessions/s/performance-ack", "POST"],
    ["/api/v1/realtime-speech/sessions/s/delivery-metrics", "POST"],
    ["/api/v1/realtime-speech/sessions/s/web-heartbeat", "POST"],
    ["/api/v1/realtime-speech/desktop-devices/d/heartbeat", "POST"],
    ["/api/v1/realtime-speech/sessions/s/device-status", "POST"],
    ["/api/v1/knowledge/collections/c/uploads/quote", "POST"],
    ["/api/v1/knowledge/search", "POST"],
    ["/api/v1/billing/state", "HEAD"],
  ])("does not invalidate %s %s", (path, method) => {
    expect(isStateAffectingRequest(path, method)).toBe(false);
    const before = stateReadGeneration();
    beginStateMutation(path, method)();
    expect(stateReadGeneration()).toBe(before);
  });
});
