import { afterEach, describe, expect, it, vi } from "vitest";
import { CompanionWindowVisibility } from "../src/main/window-visibility";

const setup = () => {
  const surfaces = { hideWindow: vi.fn(), showWindow: vi.fn(), skipTaskbar: vi.fn(), setTrayTransparent: vi.fn(), hideDock: vi.fn(), showDock: vi.fn(async (): Promise<void> => undefined), now: () => Date.now() };
  return { surfaces, visibility: new CompanionWindowVisibility(surfaces) };
};
const flush = async () => { for (let i = 0; i < 6; ++i) await Promise.resolve(); };
afterEach(() => vi.useRealTimers());

describe("explicit companion visibility", () => {
  it("hides the window and keeps a transparent tray and restores the same UI without capture operations", async () => {
    const { surfaces: s, visibility: v } = setup();
    v.hide();
    expect(v.isHidden()).toBe(true);
    expect(s.hideWindow).toHaveBeenCalledOnce();
    expect(s.skipTaskbar).toHaveBeenLastCalledWith(true);
    expect(s.setTrayTransparent).toHaveBeenLastCalledWith(true);
    expect(s.hideDock).toHaveBeenCalledOnce();
    v.restore(); await flush();
    expect(v.isHidden()).toBe(false);
    expect(s.setTrayTransparent).toHaveBeenLastCalledWith(false);
    expect(s.showWindow).toHaveBeenCalledOnce();
    expect(s.skipTaskbar).toHaveBeenLastCalledWith(false);
    expect(s.showDock).toHaveBeenCalledOnce();
  });
  it("keeps a recreated renderer hidden until the user restores", () => {
    const { visibility: v } = setup(), ready = vi.fn();
    v.hide(); v.showOnReady(ready); expect(ready).not.toHaveBeenCalled();
    v.restore(); v.showOnReady(ready); expect(ready).toHaveBeenCalledOnce();
  });
  it("starts every new process visible", () => {
    const { visibility: old } = setup(); old.hide(); old.dispose();
    const { visibility: fresh } = setup(); expect(fresh.isHidden()).toBe(false);
  });
  it("cancels a delayed repeated Dock hide when restore overtakes it", async () => {
    vi.useFakeTimers();
    const { surfaces: s, visibility: v } = setup();
    v.hide(); v.restore(); await flush(); v.hide();
    expect(s.hideDock).toHaveBeenCalledTimes(1);
    v.restore(); await flush(); await vi.advanceTimersByTimeAsync(2000);
    expect(s.hideDock).toHaveBeenCalledTimes(1); expect(v.isHidden()).toBe(false);
  });
  it("a late Dock show reapplies the latest hide with a timing guard", async () => {
    vi.useFakeTimers();
    const { surfaces: s, visibility: v } = setup();
    let resolve!: () => void;
    s.showDock.mockImplementation(() => new Promise<void>(done => { resolve = done; }));
    v.hide(); v.restore(); await flush(); v.hide(); resolve(); await flush();
    await vi.advanceTimersByTimeAsync(1100);
    expect(v.isHidden()).toBe(true); expect(s.hideDock).toHaveBeenCalledTimes(2);
  });
  it("an obsolete queued show never runs after a newer hide", async () => {
    const { surfaces: s, visibility: v } = setup();
    v.restore(); v.hide(); await flush(); expect(s.showDock).not.toHaveBeenCalled();
  });
  it("dispose cancels pending UI work and suppresses further restore", async () => {
    vi.useFakeTimers();
    const { surfaces: s, visibility: v } = setup(); v.hide(); v.hide(); v.dispose();
    v.restore(); v.showOnReady(s.showWindow); await vi.advanceTimersByTimeAsync(2000);
    expect(s.hideDock).toHaveBeenCalledOnce(); expect(s.showWindow).not.toHaveBeenCalled();
  });
  it("Windows needs no Dock implementation", () => {
    const s = { hideWindow: vi.fn(), showWindow: vi.fn(), skipTaskbar: vi.fn(), setTrayTransparent: vi.fn() };
    const v = new CompanionWindowVisibility(s); v.hide(); v.restore(); expect(s.showWindow).toHaveBeenCalledOnce();
  });
  it("a tray image failure cannot prevent application reopening", () => {
    const { surfaces: s, visibility: v } = setup();
    s.setTrayTransparent.mockImplementation(transparent => { if (!transparent) throw new Error("synthetic tray failure"); });
    v.hide(); expect(() => v.restore()).not.toThrow();
    expect(v.isHidden()).toBe(false); expect(s.showWindow).toHaveBeenCalledOnce();
    expect(s.skipTaskbar).toHaveBeenLastCalledWith(false);
  });
});
