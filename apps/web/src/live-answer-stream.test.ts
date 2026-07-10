import { describe, expect, it } from "vitest";

import { createSseParser, parseLiveAnswerStreamFrames } from "./live-answer-stream";

describe("live answer stream parser", () => {
  it("parses answer events from complete SSE frames", () => {
    const events = parseLiveAnswerStreamFrames([
      'event: task-started\ndata: {"type":"task-started","task":{"taskId":"task-1"}}',
      'event: chunk\ndata: {"type":"chunk","chunk":{"sequence":1,"text":"第一段","isFinal":false}}',
      "",
    ].join("\n\n"));
    expect(events.map(event => event.type)).toEqual(["task-started", "chunk"]);
    expect(events[1]?.chunk?.text).toBe("第一段");
  });

  it("buffers partial frames and emits in order", () => {
    const events: string[] = [];
    const parser = createSseParser(event => events.push(event.type));
    parser.push('event: chunk\ndata: {"type":"chunk","chunk":{"sequence":1,');
    expect(events).toEqual([]);
    parser.push('"text":"第一段","isFinal":false}}\n\n');
    parser.push('event: completed\ndata: {"type":"completed","task":{"taskId":"task-1"}}\n\n');
    expect(events).toEqual(["chunk", "completed"]);
  });
});
