import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { authClient, type StoredAuthSession } from "./auth-client";
import { interviewAppAdapter } from "./app-adapter";
import { loginDestination } from "./LoginPage";
import type { WebAppState } from "./domain";
import { syntheticState } from "../../web/src/test-state";

const state = () => structuredClone(syntheticState) as unknown as WebAppState;
function storeSession(suffix = "test"): StoredAuthSession {
  const session = { accessToken: `synthetic-access-${suffix}`, refreshToken: `synthetic-refresh-${suffix}`, account: { ...state().account, id: suffix } };
  localStorage.setItem("offersteady.auth.access_token", session.accessToken);
  localStorage.setItem("offersteady.auth.refresh_token", session.refreshToken);
  localStorage.setItem("offersteady.auth.account", JSON.stringify(session.account));
  return session;
}

describe("lightweight Global entry", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); });

  it.each([
    ["/", "AI interview guidance. Built around you."],
    ["/login", "Sign in to OfferSteady"],
    ["/pricing", "Choose the plan that fits your interview schedule."],
    ["/features", "AI interview guidance for preparation and live sessions."],
  ])("renders %s with business APIs unavailable and never requests business state", async (path, heading) => {
    window.history.replaceState({}, "", path);
    const fetch = vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("backend unavailable"));
    const load = vi.spyOn(interviewAppAdapter, "loadState");
    render(<App />);
    expect(await screen.findByRole("heading", { name: heading, level: 1 })).toBeInTheDocument();
    expect(load).not.toHaveBeenCalled();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("does not restore a session or load private data merely to show the homepage", () => {
    storeSession();
    window.history.replaceState({}, "", "/");
    const restore = vi.spyOn(authClient, "restore");
    const load = vi.spyOn(interviewAppAdapter, "loadState");
    render(<App />);
    expect(screen.getByRole("link", { name: "Open workspace" })).toHaveAttribute("href", "/app");
    expect(restore).not.toHaveBeenCalled();
    expect(load).not.toHaveBeenCalled();
  });

  it("redirects an unsigned deep link and loads state only after password login", async () => {
    window.history.replaceState({}, "", "/app/library?tab=resume#top");
    const fetch = vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("unexpected fetch"));
    const restore = vi.spyOn(authClient, "restore").mockImplementation(async () => authClient.readStoredSession()!);
    const login = vi.spyOn(authClient, "loginGlobal").mockImplementation(async () => storeSession("new-account"));
    const load = vi.spyOn(interviewAppAdapter, "loadState").mockResolvedValue(state());
    render(<App />);
    expect(await screen.findByLabelText("Email address")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/login");
    expect(load).not.toHaveBeenCalled();
    expect(fetch).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "synthetic@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "synthetic password only" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in", exact: true }));
    expect(await screen.findByRole("heading", { name: "Interview materials" })).toBeInTheDocument();
    expect(window.location.pathname + window.location.search + window.location.hash).toBe("/app/library?tab=resume#top");
    expect(login).toHaveBeenCalledOnce();
    expect(restore).toHaveBeenCalledOnce();
    expect(load).toHaveBeenCalledOnce();
    fireEvent.click(screen.getAllByRole("link", { name: "Interviews", exact: true })[0]!);
    expect(await screen.findByRole("heading", { name: "Your interviews" })).toBeInTheDocument();
    expect(load).toHaveBeenCalledOnce(); // no provider remount while navigating inside the workspace
  });

  it("rejects an expired workspace session without fetching anonymous business state", async () => {
    storeSession();
    window.history.replaceState({}, "", "/app");
    vi.spyOn(authClient, "restore").mockRejectedValue(new Error("expired"));
    const load = vi.spyOn(interviewAppAdapter, "loadState");
    render(<App />);
    expect(await screen.findByLabelText("Password")).toBeInTheDocument();
    expect(authClient.readStoredSession()).toBeNull();
    expect(load).not.toHaveBeenCalled();
  });

  it("keeps the login form usable during restore and ignores a late restore after user interaction", async () => {
    const session = storeSession();
    window.history.replaceState({}, "", "/login");
    let resolve!: (session: StoredAuthSession) => void;
    const restore = vi.spyOn(authClient, "restore").mockImplementation(() => new Promise(done => { resolve = done; }));
    const load = vi.spyOn(interviewAppAdapter, "loadState");
    render(<App />);
    expect(screen.getByLabelText("Email address")).toBeEnabled();
    fireEvent.focus(screen.getByLabelText("Email address"));
    expect(restore.mock.calls[0]?.[0]?.aborted).toBe(true);
    await act(async () => resolve(session));
    expect(window.location.pathname).toBe("/login");
    expect(load).not.toHaveBeenCalled();
  });

  it("keeps the billing return behind the workspace authentication boundary", async () => {
    window.history.replaceState({}, "", "/billing/success");
    const load = vi.spyOn(interviewAppAdapter, "loadState");
    render(<App />);
    await waitFor(() => expect(window.location.pathname).toBe("/login"));
    expect(window.history.state.usr.from).toBe("/app/billing");
    expect(load).not.toHaveBeenCalled();
  });

  it.each(["/login", "/app"])("does not clear a newer account after a cancelled restore on %s", async path => {
    storeSession("old-account");
    window.history.replaceState({}, "", path);
    vi.spyOn(authClient, "restore").mockImplementation(async () => {
      storeSession("new-account");
      throw new DOMException("Session changed", "AbortError");
    });
    render(<App />);
    await waitFor(() => expect(authClient.readStoredSession()?.account.id).toBe("new-account"));
    await act(async () => undefined);
    expect(authClient.readStoredSession()?.account.id).toBe("new-account");
  });

  it.each(["https://example.com", "//example.com", "/app\\evil", "/application", "/login"])("rejects non-workspace return path %s", value => {
    expect(loginDestination(value)).toBe("/app");
  });
});
