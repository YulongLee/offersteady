export interface DesktopCaptureRequestEvent {
  readonly requestId: string;
  readonly status: "requested";
}

export class DesktopCaptureEventParser {
  private buffer = "";
  private readonly seenRequestIds = new Set<string>();

  push(chunk: string): DesktopCaptureRequestEvent[] {
    this.buffer += chunk.replace(/\r\n/g, "\n");
    const requests: DesktopCaptureRequestEvent[] = [];
    let boundary = this.buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const frame = this.buffer.slice(0, boundary);
      this.buffer = this.buffer.slice(boundary + 2);
      const eventName = frame.split("\n").find(line => line.startsWith("event:"))?.slice(6).trim();
      const data = frame.split("\n").filter(line => line.startsWith("data:")).map(line => line.slice(5).trim()).join("\n");
      if (eventName === "capture-request" && data) {
        try {
          const payload = JSON.parse(data) as { requestId?: string; status?: string };
          if (payload.status === "requested" && payload.requestId && !this.seenRequestIds.has(payload.requestId)) {
            this.seenRequestIds.add(payload.requestId);
            requests.push({ requestId: payload.requestId, status: "requested" });
          }
        } catch {
          // Ignore a malformed frame and continue consuming subsequent events.
        }
      }
      boundary = this.buffer.indexOf("\n\n");
    }
    return requests;
  }
}
