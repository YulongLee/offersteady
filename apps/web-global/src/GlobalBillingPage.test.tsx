import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { authClient, type StoredAuthSession } from "./auth-client";
import { BillingPage } from "./GlobalBillingPage";
import type { WebAppState } from "./domain";

const session: StoredAuthSession = {
  accessToken: "access-token",
  refreshToken: "refresh-token",
  account: { id: "user-1", displayName: "Test user", createdAtMs: 1, bindings: [] },
};

const statePayload = {
  entitlement: {
    offerCode: "global-job-hunt",
    endsAtMs: Date.now() + 10 * 86_400_000,
    knowledgeTokensRemaining: 900_000,
    benefits: { knowledgeTokens: 1_000_000 },
  },
  usage: {
    copilotMinutesRemaining: null,
    screenAssistUsesRemaining: null,
    copilotUnlimited: true,
    screenAssistUnlimited: true,
    knowledgeTokensRemaining: 900_000,
    knowledgeTokensUnlimited: false,
  },
  knowledge: { remaining: 900_000, unlimited: false },
  orders: [],
  subscription: null,
};

const envelope = <T,>(data: T) => JSON.stringify({ success: true, data, error: null, requestId: "test", meta: { apiVersion: "v1", timestamp: new Date().toISOString() } });

describe("Global billing membership status", () => {
  beforeEach(() => {
    vi.spyOn(authClient, "readStoredSession").mockReturnValue(session);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("shows the server-provided plan, expiry and remaining time", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes("/catalogue")) return new Response(envelope(null), { status: 503, headers: { "content-type": "application/json" } });
      return new Response(envelope(statePayload), { status: 200, headers: { "content-type": "application/json" } });
    }));

    render(<BillingPage state={{} as WebAppState} />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "Job Hunt" })).toBeInTheDocument());
    expect(screen.getByText(/Access through/)).toBeInTheDocument();
    expect(screen.getByText(/days remaining/)).toBeInTheDocument();
    expect(screen.getByText("900,000")).toBeInTheDocument();
  });

  it("surfaces a state error and lets the user retry instead of hiding membership", async () => {
    let failed = true;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes("/catalogue")) return new Response(envelope(null), { status: 503, headers: { "content-type": "application/json" } });
      if (failed) return new Response(envelope(null), { status: 503, headers: { "content-type": "application/json" } });
      return new Response(envelope(statePayload), { status: 200, headers: { "content-type": "application/json" } });
    }));

    render(<BillingPage state={{} as WebAppState} />);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Access status unavailable" })).toBeInTheDocument());
    failed = false;
    fireEvent.click(screen.getByRole("button", { name: "Refresh access status" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Job Hunt" })).toBeInTheDocument());
  });
});
