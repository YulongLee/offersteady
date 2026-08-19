import { describe, expect, it } from "vitest";

import { DesktopCaptureEventParser } from "../src/main/capture-event-stream";

describe("DesktopCaptureEventParser", () => {
  it("delivers a fragmented capture request as soon as its SSE frame completes", () => {
    const parser = new DesktopCaptureEventParser();
    expect(parser.push("event: capture-request\ndata: {\"requestId\":\"shot-1\",")).toEqual([]);
    expect(parser.push("\"status\":\"requested\"}\n\n")).toEqual([{ requestId: "shot-1", status: "requested" }]);
  });

  it("suppresses duplicate requests and ignores keepalive or malformed frames", () => {
    const parser = new DesktopCaptureEventParser();
    const frame = "event: capture-request\ndata: {\"requestId\":\"shot-2\",\"status\":\"requested\"}\n\n";
    expect(parser.push(`: keepalive\n\n${frame}${frame}event: capture-request\ndata: broken\n\n`)).toEqual([
      { requestId: "shot-2", status: "requested" },
    ]);
  });
});
