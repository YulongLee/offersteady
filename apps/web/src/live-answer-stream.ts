import type { SubmitManualAnswerResult } from "./domain";

export type LiveAnswerStreamEventType = "task-started" | "chunk" | "completed" | "failed" | "cancelled";

export interface LiveAnswerStreamEvent {
  readonly type: LiveAnswerStreamEventType;
  readonly task?: unknown;
  readonly chunk?: {
    readonly sequence: number;
    readonly text: string;
    readonly isFinal: boolean;
  };
  readonly errorCode?: string;
  readonly errorMessage?: string;
  readonly partialText?: string;
}

export interface ManualAnswerStreamUpdate {
  readonly result: SubmitManualAnswerResult;
  readonly event: LiveAnswerStreamEvent;
}

const parseSseFrame = (frame: string): LiveAnswerStreamEvent | null => {
  const dataLines = frame
    .split(/\r?\n/)
    .filter(line => line.startsWith("data:"))
    .map(line => line.slice(5).trimStart());
  if (!dataLines.length) return null;
  try {
    const parsed = JSON.parse(dataLines.join("\n")) as LiveAnswerStreamEvent;
    return typeof parsed.type === "string" ? parsed : null;
  } catch {
    return null;
  }
};

export const parseLiveAnswerStreamFrames = (input: string): LiveAnswerStreamEvent[] =>
  input
    .split(/\n\n+/)
    .map(frame => parseSseFrame(frame))
    .filter((event): event is LiveAnswerStreamEvent => event !== null);

export const createSseParser = (onEvent: (event: LiveAnswerStreamEvent) => void) => {
  let buffer = "";
  return {
    push(chunk: string) {
      buffer += chunk;
      const frames = buffer.split(/\n\n+/);
      buffer = frames.pop() ?? "";
      frames.forEach(frame => {
        const event = parseSseFrame(frame);
        if (event) onEvent(event);
      });
    },
    flush() {
      const event = parseSseFrame(buffer);
      buffer = "";
      if (event) onEvent(event);
    },
  };
};
