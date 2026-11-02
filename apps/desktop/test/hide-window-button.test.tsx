// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HideWindowButton } from "../src/renderer/HideWindowButton";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
describe("local hide action", () => {
  it("calls only the window IPC and explains transparent icon recovery", async () => {
    const hideWindow = vi.fn(async () => ({ hidden: true, restoreShortcut: null }));
    Object.defineProperty(window, "offersteady", { configurable: true, value: { hideWindow, getWindowVisibility: async () => ({ hidden: false, restoreShortcut: null }) } });
    render(<HideWindowButton />);
    const button = screen.getByRole("button", { name: "隐藏伴随助手" });
    expect(button.getAttribute("title")).toContain("点击原菜单栏／托盘图标位置");
    fireEvent.click(button);
    await waitFor(() => expect(hideWindow).toHaveBeenCalledOnce());
  });
  it("failed hide can be retried and an available shortcut appears only in the tooltip", async () => {
    const hideWindow = vi.fn().mockRejectedValueOnce(new Error("synthetic")).mockResolvedValue({ hidden: true, restoreShortcut: "CommandOrControl+Shift+H" });
    Object.defineProperty(window, "offersteady", { configurable: true, value: { hideWindow, getWindowVisibility: async () => ({ hidden: false, restoreShortcut: "CommandOrControl+Shift+H" }) } });
    render(<HideWindowButton />);
    const button = screen.getByRole("button", { name: "隐藏伴随助手" });
    await waitFor(() => expect(button.getAttribute("title")).toContain("Shift + H"));
    fireEvent.click(button); await screen.findByText("重试隐藏"); fireEvent.click(button);
    await waitFor(() => expect(hideWindow).toHaveBeenCalledTimes(2));
  });
});
