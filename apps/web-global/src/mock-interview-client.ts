import { createJsonClient, withBaseUrl } from "./api-client";
import { authClient } from "./auth-client";
import { readRuntimeConfig } from "./runtime-config";

const config = readRuntimeConfig(import.meta.env);
const client = createJsonClient({ baseUrl: config.apiBaseUrl });
export interface MockRound { question_id: string; question: string; answer: string | null; submission_id: string | null }
export interface MockSession {
  sessionId: string; title: string; targetRole: string; billingClass: "points" | "daily_pass_free";
  refunded: boolean; createdAtMs: number; resumeId: string | null; resumeVersion: string | null;
  error: string | null; billableMs: number; billedMinutes: number; interacting: boolean; partial: boolean;
  state: { phase: "preparing" | "generating_question" | "speaking" | "listening" | "paused" | "generating_report" | "completed";
    version: number; rounds: MockRound[]; capture_epoch: string | null };
  report: { summary: string; overall_score: number | null; dimensions: Record<string, number> | null;
    feedback: { question_id: string; answer_quote: string; strength: string; improvement: string; suggestion: string }[];
    practice_priorities: string[] } | null;
}
export interface MockQuote { eligible: boolean; dailyLimit: number; timezone: "UTC"; activeTimeMember: boolean; dailyFreeRemaining: number; entryPoints: number;
  minutePoints: number; billingClass: "points" | "daily_pass_free"; savedCount: number; savedLimit: number }
export interface MockResume { documentId: string; displayName: string; documentVersionId: string; status: string; indexState: string }

export const mockRequest = <T>(path: string, body?: unknown, method?: string): Promise<T> => {
  const session = authClient.readStoredSession();
  return client.request<T>(`/api/v1${path}`, {
    method: method ?? (body === undefined ? "GET" : "POST"),
    headers: session ? { Authorization: `Bearer ${session.accessToken}` } : {},
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
};

export const mockSocketUrl = (id: string): string => {
  const url = new URL(withBaseUrl(config.apiBaseUrl, `/api/v1/mock-interviews/${encodeURIComponent(id)}/control`), window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
};

export const MOCK_WAVEFORM_BARS = 21;
export interface MockPlaybackFrame { playing: boolean; levels: readonly number[] }
const idlePlayback: MockPlaybackFrame = { playing: false, levels: Array<number>(MOCK_WAVEFORM_BARS).fill(0) };

/** Bounded streaming PCM player. Stop invalidates already scheduled chunks. */
export class MockVoicePlayer {
  onIdle: (() => void) | null = null;
  private context: AudioContext | null = null;
  private sources = new Set<AudioBufferSourceNode>();
  private cursor = 0;
  private bytes = 0;
  private ended: (() => void) | null = null;
  private analyser: AnalyserNode | null = null;
  private samples = new Float32Array(1024);
  private observers = new Set<(frame: MockPlaybackFrame) => void>();
  private animation: number | null = null;
  private lastFrameAt = -Infinity;
  private playbackStartsAt = Infinity;
  private visualizationUnavailable = false;

  subscribePlayback(observer: (frame: MockPlaybackFrame) => void): () => void {
    this.observers.add(observer);
    observer(idlePlayback);
    this.startVisualization();
    return () => {
      this.observers.delete(observer);
      if (!this.observers.size) this.stopVisualization();
    };
  }
  private stopVisualization() {
    if (this.animation !== null) cancelAnimationFrame(this.animation);
    this.animation = null;
    this.lastFrameAt = -Infinity;
    this.samples.fill(0);
    this.observers.forEach(observer => observer(idlePlayback));
  }
  private startVisualization() {
    const context = this.context;
    if (!context || context.state !== "running" || !this.observers.size || !this.sources.size || this.animation !== null || this.visualizationUnavailable) return;
    if (!this.analyser) {
      try {
        this.analyser = context.createAnalyser();
        this.analyser.fftSize = this.samples.length;
        // Side tap only: the original source -> destination audio route is unchanged.
        for (const source of this.sources) source.connect(this.analyser);
      } catch {
        // An optional visual must never interrupt the question or change billing.
        this.visualizationUnavailable = true;
        this.analyser = null;
        return;
      }
    }
    const tick = (time: number) => {
      if (time - this.lastFrameAt >= 40) {
        this.lastFrameAt = time;
        const playing = context.currentTime >= this.playbackStartsAt;
        try { this.analyser!.getFloatTimeDomainData(this.samples); }
        catch { this.visualizationUnavailable = true; this.stopVisualization(); return; }
        const stride = Math.floor(this.samples.length / MOCK_WAVEFORM_BARS);
        const levels = Array.from({ length: MOCK_WAVEFORM_BARS }, (_, bar) => {
          let power = 0;
          for (let i = bar * stride; i < (bar + 1) * stride; i++) power += this.samples[i]! ** 2;
          const rms = Math.sqrt(power / stride);
          return playing && rms > 0.002 ? Math.min(1, Math.sqrt(rms) * 1.8) : 0;
        });
        this.observers.forEach(observer => observer({ playing, levels }));
      }
      this.animation = requestAnimationFrame(tick);
    };
    this.animation = requestAnimationFrame(tick);
  }
  async unlock() {
    if (!this.context) {
      this.context = new AudioContext();
      this.context.onstatechange = () => {
        if (this.context?.state === "running") this.startVisualization();
        else this.stopVisualization();
      };
    }
    await this.context.resume();
  }
  append(encoded: string) {
    const context = this.context;
    if (!context || context.state !== "running") throw new Error("Click Play question to allow audio playback.");
    const raw = atob(encoded);
    this.bytes += raw.length;
    if (raw.length % 2 || this.bytes > 24000 * 2 * 90) throw new Error("Question audio is invalid or exceeds the duration limit.");
    const data = context.createBuffer(1, raw.length / 2, 24000);
    const channel = data.getChannelData(0);
    for (let i = 0; i < channel.length; i++) {
      const value = raw.charCodeAt(i * 2) | (raw.charCodeAt(i * 2 + 1) << 8);
      channel[i] = (value >= 32768 ? value - 65536 : value) / 32768;
    }
    const source = context.createBufferSource();
    source.buffer = data;
    source.connect(context.destination);
    if (this.analyser) source.connect(this.analyser);
    const wasIdle = this.sources.size === 0;
    this.sources.add(source);
    source.onended = () => {
      this.sources.delete(source);
      source.disconnect();
      source.buffer = null;
      if (this.sources.size === 0) {
        this.playbackStartsAt = Infinity;
        this.stopVisualization();
        this.onIdle?.();
      }
      if (this.sources.size === 0 && this.ended) {
        const callback = this.ended;
        this.ended = null;
        callback();
      }
    };
    this.cursor = Math.max(this.cursor, context.currentTime + 0.04);
    if (wasIdle) this.playbackStartsAt = this.cursor;
    source.start(this.cursor);
    this.cursor += data.duration;
    this.startVisualization();
  }
  finish(onEnd: () => void) {
    this.ended = onEnd;
    if (!this.sources.size) { this.ended = null; onEnd(); }
  }
  stop() {
    this.ended = null;
    this.stopVisualization();
    this.playbackStartsAt = Infinity;
    for (const source of this.sources) {
      source.onended = null;
      source.stop();
      source.disconnect();
      source.buffer = null;
    }
    this.sources.clear();
    this.cursor = 0;
    this.bytes = 0;
  }
  close() {
    this.stop();
    const context = this.context;
    this.context = null;
    this.analyser?.disconnect();
    this.analyser = null;
    this.visualizationUnavailable = false;
    if (context) context.onstatechange = null;
    if (context && context.state !== "closed") void context.close();
  }
}
