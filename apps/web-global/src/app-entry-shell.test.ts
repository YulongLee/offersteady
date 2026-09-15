import { afterEach, describe, expect, it } from "vitest";
import { clearAppEntryShell, isGlobalAppPath } from "./app-entry-shell";

describe("global app entry shell", () => {
  afterEach(() => {
    document.documentElement.removeAttribute("data-app-entry");
    document.getElementById("app-entry-shell")?.remove();
  });

  it("recognizes the workspace route and nested routes only", () => {
    expect(isGlobalAppPath("/app")).toBe(true);
    expect(isGlobalAppPath("/app/")).toBe(true);
    expect(isGlobalAppPath("/app/live")).toBe(true);
    expect(isGlobalAppPath("/")).toBe(false);
    expect(isGlobalAppPath("/about")).toBe(false);
    expect(isGlobalAppPath("/application")).toBe(false);
  });

  it("clears only the temporary entry shell after React mounts", () => {
    document.documentElement.setAttribute("data-app-entry", "true");
    document.body.insertAdjacentHTML("afterbegin", '<div id="app-entry-shell"></div>');
    clearAppEntryShell();
    expect(document.documentElement).not.toHaveAttribute("data-app-entry");
    expect(document.getElementById("app-entry-shell")).not.toBeInTheDocument();
  });
});
