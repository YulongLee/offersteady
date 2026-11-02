import { MicrophoneAudioAdapter, type OpenAudioSource } from "./audio-source-adapter";
import { createAudioCaptureProcessor, downsampleToPcm16 } from "./realtime-publisher";
import { calculateRms } from "./signal-diagnostics";

interface Options {
  apiBaseUrl: string;
  sessionId: string;
  deviceId: string;
  manualCode: string;
  microphoneId: string;
  onState: (state: "capturing" | "paused" | "error", message: string) => void;
  onLevel?: (level: number) => void;
  onPermission?: (granted: boolean) => void;
}

const RESUME_TIMEOUT_MS = 3_000;
const TRACK_MUTE_GRACE_MS = 1_500;
const CONTEXT_CLOSE_TIMEOUT_MS = 1_000;

class MockCaptureUnavailable extends Error {
  constructor(readonly reason: "context" | "ended" | "muted") {
    super(reason);
  }
}

export const mockMicrophoneFailureMessage = (error: unknown): string => {
  if (error instanceof MockCaptureUnavailable) {
    if (error.reason === "ended") return "模拟面试麦克风已断开。请检查或切换设备，然后点击“重试麦克风”。";
    if (error.reason === "muted") return "模拟面试麦克风暂时无法提供声音。请检查设备，然后点击“重试麦克风”。";
    return "模拟面试收音已中断。请点击“重试麦克风”恢复。";
  }
  const name = error instanceof Error ? error.name : "";
  if (name === "NotAllowedError" || name === "SecurityError") {
    return "模拟面试麦克风权限被拒绝。请在系统设置中允许麦克风，然后点击“重试麦克风”。";
  }
  if (name === "NotFoundError" || name === "OverconstrainedError") {
    return "模拟面试没有找到可用麦克风。请连接或选择麦克风，然后点击“重试麦克风”。";
  }
  if (name === "NotReadableError") {
    return "模拟面试麦克风暂时不可读，可能被其他程序占用。请检查设备，然后点击“重试麦克风”。";
  }
  return "模拟面试麦克风启动失败。请检查麦克风和系统权限，然后点击“重试麦克风”。";
};

/** Only for mock sessions; no system source, warm buffer, VAD or quick answer. */
export class MockMicrophone {
  private stopped = false;
  private socket: WebSocket | null = null;
  private heartbeat: ReturnType<typeof setInterval> | undefined;
  private retry: ReturnType<typeof setTimeout> | undefined;
  private attempts = 0;
  private generation = 0;
  private epoch: string | null = null;
  private release: (() => Promise<void>) | null = null;
  private failureMessage: string | null = null;

  constructor(private readonly options: Options) {}

  start() {
    if (this.stopped) return;
    if (this.socket && this.socket.readyState < 2) return;
    // An explicitly replaced closed socket may not have delivered onclose yet.
    // Fence its round before installing the replacement connection.
    if (this.socket) void this.capture(null).catch(() => undefined);
    const url = new URL(`${this.options.apiBaseUrl.replace(/\/$/, "")}/mock-interviews/${encodeURIComponent(this.options.sessionId)}/microphone`);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(url);
    this.socket = socket;
    socket.onopen = () => {
      if (this.stopped || this.socket !== socket) { socket.close(); return; }
      clearInterval(this.heartbeat);
      socket.send(JSON.stringify({ deviceId: this.options.deviceId, manualCode: this.options.manualCode }));
      this.heartbeat = setInterval(() => {
        if (!this.stopped && this.socket === socket && socket.readyState === WebSocket.OPEN) socket.send('{"action":"heartbeat"}');
      }, 5000);
    };
    socket.onmessage = event => {
      if (this.stopped || this.socket !== socket) return;
      try {
        const message = JSON.parse(String(event.data)) as { type: string; epoch?: string | null; message?: string };
        if (message.type === "heartbeat") this.attempts = 0;
        if (message.type === "capture") {
          const epoch = message.epoch ?? null;
          void this.capture(epoch).catch(error => {
            if (!this.stopped && this.socket === socket && this.epoch === epoch) this.fail(error);
          });
        }
        if (message.type === "error") {
          this.failureMessage = message.message ?? "模拟面试收音连接异常";
          this.options.onState("error", this.failureMessage);
        }
      } catch {
        socket.close();
      }
    };
    socket.onclose = () => {
      if (this.socket !== socket) return;
      clearInterval(this.heartbeat);
      this.heartbeat = undefined;
      this.socket = null;
      void this.capture(null).catch(() => undefined);
      if (!this.stopped) {
        if (!this.failureMessage) this.options.onState("paused", "模拟面试收音已暂停，正在重新连接。");
        this.retry = setTimeout(() => this.start(), Math.min(10000, 1000 * 2 ** Math.min(this.attempts++, 4)));
      }
    };
  }

  private fail(error: unknown) {
    if (this.stopped) return;
    this.failureMessage = mockMicrophoneFailureMessage(error);
    // Failure fences PCM synchronously. Reopening requires the existing explicit
    // retry path; an input or AudioContext failure must not reconnect itself.
    void this.stop().catch(() => undefined);
    this.options.onState("error", this.failureMessage);
  }

  private async capture(epoch: string | null) {
    if (epoch === this.epoch) return;
    if (epoch !== null && !/^[a-f0-9]{32}$/.test(epoch)) throw new Error("invalid-mock-epoch");
    const generation = ++this.generation;
    const ownerSocket = this.socket;
    const currentOwner = () => !this.stopped && generation === this.generation
      && this.socket === ownerSocket && this.epoch === epoch;
    this.epoch = epoch;
    const previous = this.release;
    this.release = null;
    await previous?.();
    if (!currentOwner() || !epoch) {
      if (currentOwner() && !this.failureMessage) this.options.onState("paused", "AI 面试官提问中，麦克风不会上传。");
      return;
    }
    let media: OpenAudioSource;
    try {
      media = await new MicrophoneAudioAdapter().open(this.options.microphoneId);
    } catch (error) {
      if (!currentOwner()) return;
      // Only acquisition denial is evidence of microphone permission failure.
      // A similarly named AudioContext error is a separate audio-engine fault.
      if (error instanceof Error && (error.name === "NotAllowedError" || error.name === "SecurityError")) this.options.onPermission?.(false);
      if (currentOwner()) this.fail(error);
      return;
    }
    if (!currentOwner()) { media.close(); return; }
    this.options.onPermission?.(true);
    let context: AudioContext | null = null;
    let source: MediaStreamAudioSourceNode | null = null;
    let processor: Awaited<ReturnType<typeof createAudioCaptureProcessor>> | null = null;
    let released = false;
    let captureReady = false;
    let cancelResume: (() => void) | null = null;
    let muteTimer: ReturnType<typeof setTimeout> | undefined;
    const tracks = media.stream.getAudioTracks();
    const current = () => currentOwner() && !released;
    const quietly = (work: () => unknown) => { try { work(); } catch { /* Continue releasing the remaining resources. */ } };
    const detachProcessor = (value: NonNullable<typeof processor>) => {
      quietly(() => value.detach());
      quietly(() => value.processor.disconnect());
      quietly(() => value.sink.disconnect());
    };
    const contextUnavailable = () => {
      if (current() && captureReady && context?.state !== "running") this.fail(new MockCaptureUnavailable("context"));
    };
    const inputEnded = () => {
      if (current()) this.fail(new MockCaptureUnavailable("ended"));
    };
    const updateMute = () => {
      if (!current() || !tracks.some(track => track.muted)) {
        clearTimeout(muteTimer);
        muteTimer = undefined;
        return;
      }
      if (muteTimer !== undefined) return;
      muteTimer = setTimeout(() => {
        muteTimer = undefined;
        if (current() && tracks.some(track => track.muted)) this.fail(new MockCaptureUnavailable("muted"));
      }, TRACK_MUTE_GRACE_MS);
    };
    const release = async () => {
      if (released) return;
      released = true;
      cancelResume?.();
      clearTimeout(muteTimer);
      context?.removeEventListener("statechange", contextUnavailable);
      for (const track of tracks) {
        track.removeEventListener("ended", inputEnded);
        track.removeEventListener("mute", updateMute);
        track.removeEventListener("unmute", updateMute);
      }
      if (processor) detachProcessor(processor);
      quietly(() => source?.disconnect());
      quietly(() => media.close());
      // Input tracks and callbacks are already stopped. A stalled close must
      // not indefinitely block stop or a later round; still observe rejection.
      if (context && context.state !== "closed") {
        let timer: ReturnType<typeof setTimeout> | undefined;
        try {
          await Promise.race([
            context.close().catch(() => undefined),
            new Promise<void>(resolve => { timer = setTimeout(resolve, CONTEXT_CLOSE_TIMEOUT_MS); }),
          ]);
        } catch { /* A closing context cannot revive fenced input. */ }
        finally { clearTimeout(timer); }
      }
    };
    this.release = release;
    try {
      if (!current()) { await release(); return; }
      context = new AudioContext({ latencyHint: "interactive" });
      const captureContext = context;
      captureContext.addEventListener("statechange", contextUnavailable);
      for (const track of tracks) {
        track.addEventListener("ended", inputEnded);
        track.addEventListener("mute", updateMute);
        track.addEventListener("unmute", updateMute);
      }
      if (!tracks.length || tracks.some(track => track.readyState === "ended")) throw new MockCaptureUnavailable("ended");
      const prefix = new TextEncoder().encode(epoch);
      // Fixed 100 ms PCM buffer, cleared for every round; never replay old audio.
      let pending = new Uint8Array(3200);
      let offset = 0;
      let lastLevelAtMs = -Infinity;
      const openedProcessor = await createAudioCaptureProcessor(captureContext, samples => {
        const socket = this.socket;
        if (!current() || !captureReady || captureContext.state !== "running" || socket?.readyState !== WebSocket.OPEN) return;
        if (socket.bufferedAmount > 64000) {
          socket.close(); // Fail closed instead of buffering minutes of stale audio.
          return;
        }
        const nowMs = Date.now();
        if (this.options.onLevel && nowMs - lastLevelAtMs >= 100) {
          lastLevelAtMs = nowMs;
          this.options.onLevel(calculateRms(samples));
        }
        if (!current() || this.socket !== socket || socket.readyState !== WebSocket.OPEN) return;
        const pcm = downsampleToPcm16(samples, captureContext.sampleRate);
        let index = 0;
        while (index < pcm.length) {
          const count = Math.min(pcm.length - index, pending.length - offset);
          pending.set(pcm.subarray(index, index + count), offset);
          index += count;
          offset += count;
          if (offset === pending.length) {
            const frame = new Uint8Array(32 + pending.length);
            frame.set(prefix);
            frame.set(pending, 32);
            socket.send(frame);
            pending = new Uint8Array(3200);
            offset = 0;
          }
        }
      });
      if (!current()) { detachProcessor(openedProcessor); await release(); return; }
      processor = openedProcessor;
      source = captureContext.createMediaStreamSource(media.stream);
      source.connect(processor.processor);
      await new Promise<void>((resolve, reject) => {
        let settled = false;
        let timer: ReturnType<typeof setTimeout> | undefined;
        const finish = (failed = false) => {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          cancelResume = null;
          if (failed) reject(new MockCaptureUnavailable("context"));
          else resolve();
        };
        cancelResume = () => finish();
        timer = setTimeout(() => finish(true), RESUME_TIMEOUT_MS);
        try { void Promise.resolve(captureContext.resume()).then(() => finish(), () => finish(true)); }
        catch { finish(true); }
      });
      if (!current()) { await release(); return; }
      if (captureContext.state !== "running") throw new MockCaptureUnavailable("context");
      if (tracks.some(track => track.readyState === "ended")) throw new MockCaptureUnavailable("ended");
      captureReady = true;
      updateMute();
      if (current()) {
        this.failureMessage = null;
        this.options.onState("capturing", "模拟面试：麦克风已就绪，等待你的回答。");
      }
    } catch (error) {
      const audioError = error instanceof Error && (error.name === "NotAllowedError" || error.name === "SecurityError")
        ? new MockCaptureUnavailable("context") : error;
      if (current()) this.fail(audioError);
      await release();
    }
  }

  async stop() {
    this.stopped = true;
    ++this.generation;
    this.epoch = null;
    clearInterval(this.heartbeat);
    clearTimeout(this.retry);
    const socket = this.socket;
    this.socket = null;
    socket?.close();
    const release = this.release;
    this.release = null;
    await release?.();
  }
}
