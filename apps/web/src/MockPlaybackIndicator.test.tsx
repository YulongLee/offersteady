import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MockPlaybackIndicator } from "./MockPlaybackIndicator";
import { MOCK_WAVEFORM_BARS, type MockPlaybackFrame, type MockVoicePlayer } from "./mock-interview-client";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
function setup(reduced = false) {
  let observer: (frame: MockPlaybackFrame) => void = () => {};
  const unsubscribe = vi.fn();
  const preference = { matches: reduced, addEventListener: vi.fn(), removeEventListener: vi.fn() };
  vi.stubGlobal("matchMedia", vi.fn(() => preference));
  const player = { subscribePlayback: vi.fn(callback => { observer = callback; return unsubscribe; }) } as unknown as MockVoicePlayer;
  return { player, unsubscribe, preference, emit: (playing: boolean, volume = 0.6) => act(() => observer({ playing, levels: Array(MOCK_WAVEFORM_BARS).fill(volume) })) };
}
it("shows actual playback beneath the portrait, with quiet waiting and immediate idle", () => {
  const state = setup(); const view = render(<MockPlaybackIndicator player={state.player} phase="speaking" />);
  expect(screen.getByRole("status").textContent).toBe("等待语音播放");
  state.emit(true);
  expect(screen.getByRole("status").textContent).toBe("面试官正在提问");
  expect(view.container.querySelector<HTMLElement>(".mock-waveform > span")!.style.transform).not.toBe("scaleY(0.12)");
  state.emit(false, 0);
  expect(view.container.querySelector<HTMLElement>(".mock-waveform > span")!.style.transform).toBe("scaleY(0.12)");
  view.rerender(<MockPlaybackIndicator player={state.player} phase="paused" />);
  expect(screen.getByRole("status").textContent).toBe("语音播放已暂停");
  view.unmount(); expect(state.unsubscribe).toHaveBeenCalled();
  expect(state.preference.removeEventListener).toHaveBeenCalled();
});
it("keeps static bars but announces playback under reduced motion", () => {
  const state = setup(true); const view = render(<MockPlaybackIndicator player={state.player} phase="speaking" />);
  state.emit(true);
  expect(screen.getByRole("status").textContent).toBe("面试官正在提问");
  expect(view.container.querySelector(".is-reduced-motion")).not.toBeNull();
  expect([...view.container.querySelectorAll<HTMLElement>(".mock-waveform > span")].every(bar => bar.style.transform === "scaleY(0.12)")).toBe(true);
  state.emit(false); expect(screen.getByRole("status").textContent).toBe("等待语音播放");
});
