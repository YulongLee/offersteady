import { MicrophoneAudioAdapter } from "./audio-source-adapter";
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

export const mockMicrophoneFailureMessage = (error: unknown): string => {
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
    const url = new URL(`${this.options.apiBaseUrl.replace(/\/$/, "")}/mock-interviews/${encodeURIComponent(this.options.sessionId)}/microphone`);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(url);
    this.socket = socket;
    socket.onopen = () => {
      if (this.stopped || this.socket !== socket) { socket.close(); return; }
      socket.send(JSON.stringify({ deviceId: this.options.deviceId, manualCode: this.options.manualCode }));
      this.heartbeat = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) socket.send('{"action":"heartbeat"}');
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
            if (this.stopped || this.socket !== socket || this.epoch !== epoch) return;
            this.failureMessage = mockMicrophoneFailureMessage(error);
            if (error instanceof Error && (error.name === "NotAllowedError" || error.name === "SecurityError")) this.options.onPermission?.(false);
            // OS/device errors need explicit recovery, not repeated permission attempts.
            void this.stop().catch(() => undefined);
            this.options.onState("error", this.failureMessage);
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
      void this.capture(null).catch(() => undefined);
      if (!this.stopped) {
        if (!this.failureMessage) this.options.onState("paused", "模拟面试收音已暂停，正在重新连接。");
        this.retry = setTimeout(() => this.start(), Math.min(10000, 1000 * 2 ** Math.min(this.attempts++, 4)));
      }
    };
  }

  private async capture(epoch: string | null) {
    if (epoch === this.epoch) return;
    if (epoch !== null && !/^[a-f0-9]{32}$/.test(epoch)) throw new Error("invalid-mock-epoch");
    const generation = ++this.generation;
    this.epoch = epoch;
    const previous = this.release;
    this.release = null;
    await previous?.();
    if (this.stopped || generation !== this.generation || !epoch) {
      if (!this.stopped && !this.failureMessage && generation === this.generation) this.options.onState("paused", "AI 面试官提问中，麦克风不会上传。");
      return;
    }
    const media = await new MicrophoneAudioAdapter().open(this.options.microphoneId);
    if (this.stopped || generation !== this.generation) { media.close(); return; }
    this.options.onPermission?.(true);
    let context: AudioContext | null = null;
    let source: MediaStreamAudioSourceNode | null = null;
    let processor: Awaited<ReturnType<typeof createAudioCaptureProcessor>> | null = null;
    let released = false;
    const release = async () => {
      if (released) return;
      released = true;
      processor?.detach();
      source?.disconnect();
      processor?.processor.disconnect();
      processor?.sink.disconnect();
      media.close();
      if (context && context.state !== "closed") await context.close();
    };
    try {
      context = new AudioContext({ latencyHint: "interactive" });
      const captureContext = context;
      const prefix = new TextEncoder().encode(epoch);
      // Fixed 100 ms PCM buffer, cleared for every round; never replay old audio.
      let pending = new Uint8Array(3200);
      let offset = 0;
      let lastLevelAtMs = -Infinity;
      processor = await createAudioCaptureProcessor(captureContext, samples => {
        const socket = this.socket;
        if (this.stopped || generation !== this.generation || socket?.readyState !== WebSocket.OPEN) return;
        if (socket.bufferedAmount > 64000) {
          socket.close(); // Fail closed instead of buffering minutes of stale audio.
          return;
        }
        const nowMs = Date.now();
        if (this.options.onLevel && nowMs - lastLevelAtMs >= 100) {
          lastLevelAtMs = nowMs;
          this.options.onLevel(calculateRms(samples));
        }
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
      if (this.stopped || generation !== this.generation) { await release(); return; }
      this.release = release;
      source = captureContext.createMediaStreamSource(media.stream);
      source.connect(processor.processor);
      await captureContext.resume();
      if (!this.stopped && generation === this.generation) {
        this.failureMessage = null;
        this.options.onState("capturing", "模拟面试：麦克风已就绪，等待你的回答。");
      }
    } catch (error) {
      if (this.release === release) this.release = null;
      await release();
      throw error;
    }
  }

  async stop() {
    this.stopped = true;
    ++this.generation;
    this.epoch = null;
    clearInterval(this.heartbeat);
    clearTimeout(this.retry);
    this.socket?.close();
    this.socket = null;
    const release = this.release;
    this.release = null;
    await release?.();
  }
}
