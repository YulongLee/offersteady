import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { MockVoicePlayer } from "./mock-interview-client";

let sources: any[];
let context: any;
let player: MockVoicePlayer;
let frames: Map<number, FrameRequestCallback>;
let frameId: number;
let sampleVolume: number;
let analyser: any;
function tick(time: number) {
  const callbacks = [...frames.values()]; frames.clear();
  callbacks.forEach(callback => callback(time));
}
beforeEach(() => {
  sources = [];
  frames = new Map(); frameId = 0; sampleVolume = 0;
  analyser = { fftSize: 0, disconnect: vi.fn(), getFloatTimeDomainData: vi.fn((samples: Float32Array) => samples.fill(sampleVolume)) };
  vi.stubGlobal("requestAnimationFrame", vi.fn((callback: FrameRequestCallback) => { frames.set(++frameId, callback); return frameId; }));
  vi.stubGlobal("cancelAnimationFrame", vi.fn((id: number) => frames.delete(id)));
  vi.stubGlobal("AudioContext", class {
    state = "running"; currentTime = 1; destination = {};
    onstatechange: (() => void) | null = null;
    createAnalyser = vi.fn(() => analyser);
    resume = vi.fn(async () => {}); close = vi.fn(async () => { this.state = "closed"; });
    createBuffer = (_channels: number, length: number, rate: number) => ({ duration: length / rate, getChannelData: () => new Float32Array(length) });
    createBufferSource = () => { const source = { buffer: null, onended: null, connect: vi.fn(), disconnect: vi.fn(), start: vi.fn(), stop: vi.fn() }; sources.push(source); return source; };
    constructor() { context = this; }
  });
  player = new MockVoicePlayer();
});
afterEach(() => { player.close(); vi.useRealTimers(); vi.unstubAllGlobals(); });

it("requires playback permission and rejects malformed PCM", async () => {
  expect(() => player.append("AAA=")).toThrow("点击朗读");
  await player.unlock(); expect(() => player.append("AA==")).toThrow("格式异常");
});
it("waits for every scheduled chunk before starting listening", async () => {
  await player.unlock(); player.append("AAA="); player.append("AAA=");
  const end = vi.fn(); player.finish(end);
  const idle = vi.fn(); player.onIdle = idle;
  sources[0].onended(); expect(end).not.toHaveBeenCalled();
  sources[1].onended(); expect(end).toHaveBeenCalledOnce();
  expect(idle).toHaveBeenCalledOnce();
  expect(sources.every(source => source.buffer === null)).toBe(true);
});
it("pause/close clears buffers and prevents stale playback callbacks", async () => {
  await player.unlock(); player.append("AAA="); const end = vi.fn(); player.finish(end);
  player.stop(); expect(sources[0].onended).toBeNull(); expect(sources[0].buffer).toBeNull();
  expect(sources[0].stop).toHaveBeenCalledOnce(); expect(end).not.toHaveBeenCalled();
  player.close(); expect(context.close).toHaveBeenCalledOnce();
});

it("meters actual audio only after playback starts; silence has no fabricated waveform", async () => {
  const observe = vi.fn(); player.subscribePlayback(observe);
  await player.unlock(); expect(frames.size).toBe(0);
  player.append("AAA="); expect(frames.size).toBe(1);
  expect(sources[0].connect).toHaveBeenCalledWith(context.destination);
  expect(sources[0].connect).toHaveBeenCalledWith(analyser);
  sampleVolume = 0.1; tick(0);
  expect(observe.mock.lastCall![0].playing).toBe(false);
  expect(observe.mock.lastCall![0].levels.every((level: number) => level === 0)).toBe(true);
  context.currentTime = 1.1; tick(40);
  expect(observe.mock.lastCall![0].playing).toBe(true);
  const quiet = observe.mock.lastCall![0].levels[0];
  sampleVolume = 0.25; tick(80);
  expect(observe.mock.lastCall![0].levels[0]).toBeGreaterThan(quiet);
  sampleVolume = 0; tick(120);
  expect(observe.mock.lastCall![0].levels.every((level: number) => level === 0)).toBe(true);
  const calls = observe.mock.calls.length; tick(130);
  expect(observe).toHaveBeenCalledTimes(calls);
});

it("keeps a single loop across chunks and releases it on drain, stop and close", async () => {
  const observe = vi.fn(); player.subscribePlayback(observe);
  await player.unlock(); player.append("AAA="); player.append("AAA=");
  expect(frames.size).toBe(1); expect(context.createAnalyser).toHaveBeenCalledOnce();
  sources[0].onended(); expect(frames.size).toBe(1);
  sources[1].onended(); expect(frames.size).toBe(0);
  expect(observe.mock.lastCall![0].playing).toBe(false);
  player.append("AAA="); expect(frames.size).toBe(1);
  player.stop(); expect(frames.size).toBe(0);
  expect(observe.mock.lastCall![0].levels.every((level: number) => level === 0)).toBe(true);
  player.append("AAA="); player.close();
  expect(frames.size).toBe(0); expect(analyser.disconnect).toHaveBeenCalledOnce();
  expect(context.onstatechange).toBeNull();
});

it("suspension and unsubscribe stop analysis without affecting playback or billing callbacks", async () => {
  const observe = vi.fn(); const idle = vi.fn(); player.onIdle = idle;
  await player.unlock(); player.append("AAA="); expect(context.createAnalyser).not.toHaveBeenCalled();
  const unsubscribe = player.subscribePlayback(observe); expect(frames.size).toBe(1);
  context.state = "suspended"; context.onstatechange();
  expect(frames.size).toBe(0); expect(observe.mock.lastCall![0].playing).toBe(false);
  context.state = "running"; context.onstatechange(); expect(frames.size).toBe(1);
  unsubscribe(); expect(frames.size).toBe(0);
  expect(sources[0].stop).not.toHaveBeenCalled(); expect(idle).not.toHaveBeenCalled();
  expect(sources[0].buffer).not.toBeNull();
});

it("an unavailable visual analyser does not stop audio or its completion callback", async () => {
  player.subscribePlayback(vi.fn()); await player.unlock();
  context.createAnalyser.mockImplementation(() => { throw new Error("unavailable"); });
  expect(() => player.append("AAA=")).not.toThrow();
  expect(sources[0].start).toHaveBeenCalledOnce(); expect(frames.size).toBe(0);
  const end = vi.fn(); player.finish(end); sources[0].onended();
  expect(end).toHaveBeenCalledOnce();
});

it("analysis failure mid-playback degrades silently without stopping the source", async () => {
  const observe = vi.fn(); player.subscribePlayback(observe); await player.unlock(); player.append("AAA=");
  analyser.getFloatTimeDomainData.mockImplementation(() => { throw new Error("closed analyser"); });
  expect(() => tick(40)).not.toThrow(); expect(frames.size).toBe(0);
  expect(sources[0].stop).not.toHaveBeenCalled(); expect(observe.mock.lastCall![0].playing).toBe(false);
});


it("bounds pending browser resume and permits a later user-gesture retry", async () => {
  await player.unlock();
  context.state = "suspended";
  let late!: () => void;
  context.resume.mockImplementationOnce(() => new Promise<void>(resolve => { late = resolve; }));
  vi.useFakeTimers();
  const pending = player.unlock();
  const failure = expect(pending).rejects.toThrow("网页声音尚未就绪");
  await vi.advanceTimersByTimeAsync(3000); await failure;
  expect(vi.getTimerCount()).toBe(0);
  context.resume.mockImplementationOnce(async () => { context.state = "running"; });
  await player.unlock(); expect(() => player.append("AAA=")).not.toThrow();
  late();
});

it("rejects a resolved resume unless its own context is actually running", async () => {
  await player.unlock(); context.state = "suspended";
  await expect(player.unlock()).rejects.toThrow("网页声音尚未就绪");
  context.resume.mockImplementationOnce(() => { throw new Error("sync failure"); });
  await expect(player.unlock()).rejects.toThrow("网页声音尚未就绪");
});

it("close cancels pending unlocks and a stale context cannot unlock a replacement", async () => {
  await player.unlock();
  const old = context; let late!: () => void;
  old.state = "suspended"; old.resume.mockImplementationOnce(() => new Promise<void>(resolve => { late = resolve; }));
  vi.useFakeTimers();
  const pending = player.unlock(); const failure = expect(pending).rejects.toThrow("网页声音尚未就绪");
  player.close(); await failure;
  expect(vi.getTimerCount()).toBe(0);
  await player.unlock(); const fresh = context;
  old.state = "running"; late();
  expect(fresh).not.toBe(old); expect(() => player.append("AAA=")).not.toThrow();
});

it("notifies once when queued audio is interrupted after audio_end without later PCM", async () => {
  player.subscribePlayback(vi.fn());
  await player.unlock(); player.append("AAA=");
  const finish = vi.fn(); player.finish(finish);
  const unavailable = vi.fn(); player.onPlaybackUnavailable = unavailable;
  context.state = "suspended"; context.onstatechange(); context.onstatechange();
  expect(unavailable).toHaveBeenCalledOnce();
  expect(finish).not.toHaveBeenCalled();
  expect(frames.size).toBe(0);
  // The consumer owns the state transition; without a callback the original
  // visual-only suspension behavior remains unchanged.
  player.stop(); context.onstatechange();
  expect(unavailable).toHaveBeenCalledOnce();
  expect(sources[0].onended).toBeNull(); expect(sources[0].buffer).toBeNull();
});

it("does not report idle, initial unlock, teardown or a stale context as playback interruption", async () => {
  const unavailable = vi.fn(); player.onPlaybackUnavailable = unavailable;
  await player.unlock();
  const old = context; const staleHandler = old.onstatechange;
  old.state = "suspended"; old.onstatechange();
  expect(unavailable).not.toHaveBeenCalled();
  player.close(); await player.unlock(); player.append("AAA=");
  staleHandler();
  expect(unavailable).not.toHaveBeenCalled();
  player.close(); expect(unavailable).not.toHaveBeenCalled();
});

it("recreates a closed playback context for an explicit retry and disconnects its old analyser", async () => {
  player.subscribePlayback(vi.fn()); await player.unlock(); player.append("AAA=");
  const old = context;
  const unavailable = vi.fn(() => player.stop()); player.onPlaybackUnavailable = unavailable;
  old.state = "closed"; old.onstatechange();
  expect(unavailable).toHaveBeenCalledOnce();
  await player.unlock();
  expect(context).not.toBe(old); expect(old.onstatechange).toBeNull();
  expect(analyser.disconnect).toHaveBeenCalledOnce();
  expect(() => player.append("AAA=")).not.toThrow();
  expect(context.createAnalyser).toHaveBeenCalledOnce();
});
