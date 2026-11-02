import { EventEmitter } from "node:events";
import { describe, expect, it, vi } from "vitest";
vi.mock("electron", () => ({ nativeImage: {} }));
import { CompanionTrayPresentation } from "../src/main/tray-presentation";
import type { Menu, NativeImage, Tray } from "electron";

function setup(platform: string) {
  const tray = Object.assign(new EventEmitter(), { setImage: vi.fn(), setContextMenu: vi.fn(), popUpContextMenu: vi.fn(), destroy: vi.fn() });
  const images = { normal: {} as NativeImage, transparent: {} as NativeImage };
  let hidden = false;
  let presentation: CompanionTrayPresentation;
  const showMenu = vi.fn();
  const restore = vi.fn(() => { hidden = false; presentation.refresh(); });
  presentation = new CompanionTrayPresentation(tray as unknown as Tray, { platform, images, isHidden: () => hidden, restore, showMenu });
  const menu = {} as Menu;
  presentation.update(menu);
  return { tray, images, menu, restore, showMenu, presentation, hide: () => { hidden = true; presentation.refresh(); } };
}
describe("retained transparent tray recovery", () => {
  for (const platform of ["darwin", "win32"]) {
    it(`${platform}: keeps the same tray, directly restores and replaces the normal image`, () => {
      const s = setup(platform);
      s.hide(); expect(s.tray.setImage).toHaveBeenLastCalledWith(s.images.transparent);
      expect(s.tray.destroy).not.toHaveBeenCalled();
      s.tray.emit("click"); expect(s.restore).toHaveBeenCalledOnce();
      expect(s.tray.setImage).toHaveBeenLastCalledWith(s.images.normal);
      expect(s.tray.setContextMenu).toHaveBeenLastCalledWith(s.menu);
      s.tray.emit("click"); expect(s.restore).toHaveBeenCalledOnce();
    });
    it(`${platform}: capture status updates preserve transparency without duplicating listeners`, () => {
      const s = setup(platform); s.hide();
      for (let i = 0; i < 4; i++) s.presentation.update({} as Menu);
      expect(s.tray.setImage).toHaveBeenLastCalledWith(s.images.transparent);
      expect(s.tray.listenerCount("click")).toBe(1);
      s.tray.emit("click"); expect(s.restore).toHaveBeenCalledOnce();
    });
  }
  it("Mac hidden left-click bypasses the automatic menu while right-click retains the current menu", () => {
    const s = setup("darwin"); s.hide();
    expect(s.tray.setContextMenu).toHaveBeenLastCalledWith(null);
    const next = {} as Menu; s.presentation.update(next);
    s.tray.emit("right-click"); expect(s.showMenu).toHaveBeenCalledWith(next);
    expect(s.tray.popUpContextMenu).not.toHaveBeenCalled();
    expect(s.restore).not.toHaveBeenCalled();
    s.tray.emit("click"); expect(s.restore).toHaveBeenCalledOnce();
    expect(s.showMenu).toHaveBeenCalledOnce();
  });
  it("Windows retains its native right-click menu and handles double-click idempotently", () => {
    const s = setup("win32"); s.hide();
    expect(s.tray.setContextMenu).toHaveBeenLastCalledWith(s.menu);
    s.tray.emit("double-click"); s.tray.emit("click");
    expect(s.restore).toHaveBeenCalledOnce();
  });
});
