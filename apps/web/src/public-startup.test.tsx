import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { interviewAppAdapter } from "./app-adapter";
import { authClient } from "./auth-client";
import { syntheticState } from "./test-state";
import { capturePublicStartup } from "./public-startup";

afterEach(() => vi.restoreAllMocks());
const snapshot = { pathname: "/", html: '<main><h1>立即可读的公开介绍</h1><a href="/pricing">价格</a></main>' };
function pending(path = "/") {
  window.history.replaceState({}, "", path);
  vi.spyOn(authClient, "readStoredSession").mockReturnValue(null);
  return vi.spyOn(interviewAppAdapter, "loadState");
}
describe("public startup continuity", () => {
  it("keeps core HTML and links visible while the API is pending", () => {
    pending().mockReturnValue(new Promise(() => {}));
    render(<App publicStartup={snapshot} />);
    expect(screen.getByRole("heading", {name:"立即可读的公开介绍"})).toBeVisible();
    expect(screen.getByRole("link", {name:"价格"})).toHaveAttribute("href", "/pricing");
    expect(screen.queryByLabelText("页面加载中")).toBeNull();
  });
  it("preserves content after API failure and exposes retry without invented data", async () => {
    pending().mockRejectedValue(new Error("synthetic unavailable"));
    render(<App publicStartup={snapshot} />);
    expect(await screen.findByRole("button", {name:"重新加载实时信息"})).toBeVisible();
    expect(screen.getByRole("heading", {name:"立即可读的公开介绍"})).toBeVisible();
  });
  it("switches to real application content after the API resolves", async () => {
    let complete!: (state: typeof syntheticState) => void;
    pending().mockReturnValue(new Promise(resolve => { complete = resolve; }));
    render(<App publicStartup={snapshot} />);
    await act(async () => complete(structuredClone(syntheticState)));
    expect(screen.queryByText("立即可读的公开介绍")).toBeNull();
    expect(screen.getByRole("heading", {name:/让你的经历更好表达/})).toBeVisible();
  });
  it("never exposes public snapshot as private-route fallback", () => {
    pending("/app/library").mockReturnValue(new Promise(() => {}));
    render(<App publicStartup={snapshot} />);
    expect(screen.queryByText("立即可读的公开介绍")).toBeNull();
    expect(screen.getByLabelText("页面加载中")).toBeInTheDocument();
  });
  it("captures only server public entries with a heading", () => {
    const doc = new DOMParser().parseFromString('<div id="root"><h1>Public</h1></div>', 'text/html');
    for (const path of ["/", "/guide", "/terms", "/privacy"]) expect(capturePublicStartup(doc, path)?.html).toContain("Public");
    for (const path of ["/login", "/app", "/app/library", "/r/x"]) expect(capturePublicStartup(doc, path)).toBeUndefined();
  });
});
