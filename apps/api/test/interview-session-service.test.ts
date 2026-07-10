import { describe, expect, it } from "vitest";
import { InterviewSessionError, InterviewSessionService } from "../src/interview-session-service.js";

const command = { id: "start-1", idempotencyKey: "start-key", sessionId: "session-1", requestedByUserId: "user-1", inputMode: "dual-channel-audio", sourceIds: ["mic", "system"] } as const;
const ready = { ownerUserId: "user-1", microphoneGranted: true, systemAudioGranted: true } as const;

describe("interview session start", () => {
  it("starts authorized audio once and replays the same result", () => {
    const service = new InterviewSessionService();
    const first = service.start(command, ready, 10);
    expect(first.captureState).toBe("capturing");
    expect(service.start(command, ready, 20)).toEqual(first);
    expect(service.start({ ...command, id: "start-2", idempotencyKey: "other-key" }, ready, 30)).toEqual(first);
  });

  it("keeps manual start free from audio capture", () => {
    const service = new InterviewSessionService();
    expect(service.start({ ...command, inputMode: "manual", sourceIds: [] }, { ...ready, microphoneGranted: false, systemAudioGranted: false }, 10).captureState).toBe("ready");
  });

  it("requires both permissions and ownership for audio start", () => {
    const service = new InterviewSessionService();
    expect(() => service.start(command, { ...ready, systemAudioGranted: false })).toThrow(InterviewSessionError);
    expect(() => service.start(command, { ...ready, ownerUserId: "other" })).toThrow(InterviewSessionError);
  });
});
