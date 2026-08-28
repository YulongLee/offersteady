import type { AudioSourceKind } from "@offersteady/protocol";

import type { OpenAudioSource } from "./audio-source-adapter";
import { signalEvidenceIsFresh } from "./audio-readiness";

export interface WarmSourceTakeResult {
  readonly source: OpenAudioSource | null;
  readonly outcome: "promoted" | "missing" | "stale";
  readonly calibration?: AudioCalibrationSnapshot;
}

export interface AudioCalibrationSnapshot {
  readonly noiseFloor: number;
  readonly sampleCount: number;
  readonly calibratedAtMs: number;
}

export interface WarmSourceEntry {
  readonly sourceKind: AudioSourceKind;
  readonly source: OpenAudioSource;
  readonly lastSignalAtMs: number | undefined;
  readonly calibration?: AudioCalibrationSnapshot;
}

const sourceIsUsable = (source: OpenAudioSource): boolean => {
  const track = source.stream.getAudioTracks()[0];
  return Boolean(track && track.readyState === "live" && !track.muted);
};

/**
 * Owns preparation streams between React effect cleanup and live publisher
 * startup. Sources are consumable exactly once and every unconsumed source is
 * explicitly closed, so preparation audio can never accumulate or leak.
 */
export class WarmSourceHandoff {
  private readonly sources = new Map<AudioSourceKind, WarmSourceEntry>();
  private closed = false;

  constructor(entries: readonly WarmSourceEntry[] = []) {
    for (const entry of entries) this.sources.set(entry.sourceKind, entry);
  }

  take(sourceKind: AudioSourceKind, nowMs = Date.now()): WarmSourceTakeResult {
    if (this.closed) return { source: null, outcome: "missing" };
    const entry = this.sources.get(sourceKind);
    this.sources.delete(sourceKind);
    if (!entry) return { source: null, outcome: "missing" };
    if (!sourceIsUsable(entry.source) || !signalEvidenceIsFresh(entry.lastSignalAtMs, nowMs)) {
      entry.source.close();
      return { source: null, outcome: "stale" };
    }
    return {
      source: entry.source,
      outcome: "promoted",
      ...(entry.calibration ? { calibration: entry.calibration } : {}),
    };
  }

  close(): void {
    if (this.closed) return;
    this.closed = true;
    for (const entry of this.sources.values()) entry.source.close();
    this.sources.clear();
  }

  get pendingSourceCount(): number {
    return this.sources.size;
  }
}
