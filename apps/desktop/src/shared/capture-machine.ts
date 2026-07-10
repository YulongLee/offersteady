import type { CaptureState } from "@offersteady/protocol";

export type CaptureEvent =
  | "connect"
  | "permissions-granted"
  | "start"
  | "pause"
  | "resume"
  | "stop"
  | "disconnect"
  | "connection-lost"
  | "reconnected"
  | "fail";

const transitions: Readonly<Record<CaptureState, Partial<Record<CaptureEvent, CaptureState>>>> = {
  "not-connected": { connect: "permission-required" },
  "permission-required": {
    "permissions-granted": "ready",
    disconnect: "not-connected",
    fail: "error",
  },
  ready: { start: "capturing", disconnect: "not-connected", fail: "error" },
  capturing: {
    pause: "paused",
    stop: "ready",
    disconnect: "not-connected",
    "connection-lost": "reconnecting",
    fail: "error",
  },
  paused: { resume: "capturing", stop: "ready", disconnect: "not-connected", fail: "error" },
  reconnecting: {
    reconnected: "capturing",
    stop: "ready",
    disconnect: "not-connected",
    fail: "error",
  },
  error: { connect: "permission-required", disconnect: "not-connected" },
};

export const initialCaptureState = (): CaptureState => "not-connected";

export const transitionCaptureState = (
  state: CaptureState,
  event: CaptureEvent,
): CaptureState => transitions[state][event] ?? state;
