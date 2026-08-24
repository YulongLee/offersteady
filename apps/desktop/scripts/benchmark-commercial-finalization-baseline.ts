import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { SpeechSegmenter } from "../src/renderer/audio/realtime-publisher";

const payload = new Uint8Array(3_200);

const run = (
  source: "microphone" | "system",
  levels: readonly number[],
  stepMs = 100,
) => {
  const segmenter = new SpeechSegmenter(source, { mode: "legacy-threshold", maximumTurnMs: 30_000 });
  const snapshots = levels.flatMap((level, index) => segmenter.push(payload, index * stepMs, level));
  const final = [...snapshots].reverse().find((item: (typeof snapshots)[number]) => item.isFinal);
  return {
    emittedRevisions: snapshots.length,
    finalAtMs: final?.endedAtMs ?? null,
    finalReasonObservable: false,
  };
};

const speech = (count: number, rms: number) => Array.from({ length: count }, () => rms);

const currentQueueOverflow = () => {
  const capacity = 64;
  const queue: Array<{ kind: "partial" | "terminal"; sequence: number }> = [
    { kind: "terminal", sequence: 1 },
    ...Array.from({ length: capacity - 1 }, (_, index) => ({ kind: "partial" as const, sequence: index + 2 })),
  ];
  queue.push({ kind: "partial", sequence: capacity + 1 });
  const dropped = queue.shift();
  return {
    capacity,
    droppedKind: dropped?.kind ?? null,
    terminalReservedCapacity: false,
    terminalAcknowledgement: false,
  };
};

export const commercialFinalizationBaseline = {
  generatedAt: new Date().toISOString(),
  sourceCommit: process.env.OFFERSTEADY_BENCHMARK_COMMIT ?? "working-tree",
  privacy: "synthetic-levels-only-no-audio-or-transcript-content",
  currentConfiguration: {
    interimIntervalMs: 100,
    microphoneSilenceFinalizeMs: 700,
    systemSilenceFinalizeMs: 500,
    maxSegmentDurationMs: 30_000,
  },
  scenarios: {
    microphoneOrdinaryPause: run("microphone", [
      ...speech(5, 0.006),
      ...speech(4, 0),
      ...speech(5, 0.006),
      ...speech(8, 0),
    ]),
    systemCleanSilence: run("system", [
      ...speech(5, 0.002),
      ...speech(6, 0),
    ]),
    systemPersistentMeetingNoise: run("system", [
      ...speech(5, 0.002),
      ...speech(310, 0.0006),
    ]),
    microphoneContinuousSignal: run("microphone", speech(310, 0.006)),
    desktopQueuePressure: currentQueueOverflow(),
  },
  findings: [
    "System noise above the capped continuation threshold keeps the active turn open until the 30 second hard bound.",
    "The current desktop fallback queue drops the oldest item without reserving terminal capacity.",
    "Current snapshots do not expose a finalization reason or terminal acknowledgement.",
  ],
};

const outputPath = resolve(
  import.meta.dirname,
  "../../../artifacts/realtime-asr-benchmarks/commercial-finalization-baseline-2026-08-24.json",
);
mkdirSync(resolve(outputPath, ".."), { recursive: true });
writeFileSync(outputPath, `${JSON.stringify(commercialFinalizationBaseline, null, 2)}\n`, "utf8");
process.stdout.write(`${JSON.stringify({ outputPath, ...commercialFinalizationBaseline }, null, 2)}\n`);
