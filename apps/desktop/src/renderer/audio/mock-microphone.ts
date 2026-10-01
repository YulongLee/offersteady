import { MicrophoneAudioAdapter } from "./audio-source-adapter";
import { createAudioCaptureProcessor, downsampleToPcm16 } from "./realtime-publisher";

interface Options {
  apiBaseUrl: string;
  sessionId: string;
  deviceId: string;
  manualCode: string;
  microphoneId: string;
  onState: (state: "capturing" | "paused" | "error", message: string) => void;
}

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
        if (message.type === "capture") void this.capture(message.epoch ?? null).catch(() => {
          this.options.onState("error", "模拟面试麦克风启动失败，请检查权限后在网页恢复。");
          socket.close();
        });
        if (message.type === "error") this.options.onState("error", message.message ?? "模拟面试收音连接异常");
      } catch {
        socket.close();
      }
    };
    socket.onclose = () => {
      if (this.socket !== socket) return;
      clearInterval(this.heartbeat);
      void this.capture(null);
      if (!this.stopped) {
        this.options.onState("paused", "模拟面试收音已暂停，正在重新连接。");
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
      if (!this.stopped && generation === this.generation) this.options.onState("paused", "AI 面试官提问中，麦克风不会上传。");
      return;
    }
    const media = await new MicrophoneAudioAdapter().open(this.options.microphoneId);
    if (this.stopped || generation !== this.generation) { media.close(); return; }
    const context = new AudioContext({ latencyHint: "interactive" });
    let source: MediaStreamAudioSourceNode | null = null;
    let processor: Awaited<ReturnType<typeof createAudioCaptureProcessor>> | null = null;
    const release = async () => {
      processor?.detach();
      source?.disconnect();
      processor?.processor.disconnect();
      processor?.sink.disconnect();
      media.close();
      if (context.state !== "closed") await context.close();
    };
    try {
      const prefix = new TextEncoder().encode(epoch);
      // Fixed 100 ms PCM buffer, cleared for every round; never replay old audio.
      let pending = new Uint8Array(3200);
      let offset = 0;
      processor = await createAudioCaptureProcessor(context, samples => {
        const socket = this.socket;
        if (this.stopped || generation !== this.generation || socket?.readyState !== WebSocket.OPEN) return;
        if (socket.bufferedAmount > 64000) {
          socket.close(); // Fail closed instead of buffering minutes of stale audio.
          return;
        }
        const pcm = downsampleToPcm16(samples, context.sampleRate);
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
      source = context.createMediaStreamSource(media.stream);
      source.connect(processor.processor);
      await context.resume();
      if (!this.stopped && generation === this.generation) this.options.onState("capturing", "模拟面试：正在转写你的麦克风回答。");
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
