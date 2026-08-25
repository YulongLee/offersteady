import { readFileSync } from "node:fs";
import vm from "node:vm";
import { describe, expect, it } from "vitest";

interface CapturedMessage {
  readonly samples: Float32Array;
  readonly audioWorkletOutputAtMs: number;
  readonly transferred: ArrayBuffer;
  readonly callbackCount: number;
  readonly postMessageCount: number;
  readonly allocationCount: number;
}

const createProcessor = () => {
  const messages: CapturedMessage[] = [];
  let Processor: (new () => { process: (inputs: Float32Array[][], outputs: Float32Array[][]) => boolean }) | null = null;
  class AudioWorkletProcessorStub {
    readonly port = {
      postMessage: (payload: Omit<CapturedMessage, "transferred">, transferred: ArrayBuffer[]) => {
        messages.push({ ...payload, transferred: transferred[0]! });
      },
    };
  }
  const source = readFileSync(new URL("../src/renderer/audio/pcm-capture.worklet.js", import.meta.url), "utf8");
  vm.runInNewContext(source, {
    AudioWorkletProcessor: AudioWorkletProcessorStub,
    Float32Array,
    Date,
    Math,
    registerProcessor: (_name: string, constructor: typeof Processor) => { Processor = constructor; },
  });
  if (!Processor) throw new Error("worklet processor was not registered");
  const RegisteredProcessor = Processor as unknown as new () => {
    process: (inputs: Float32Array[][], outputs: Float32Array[][]) => boolean;
  };
  return { processor: new RegisteredProcessor(), messages };
};

describe("PCM capture AudioWorklet stability", () => {
  it("transfers one 1024-sample buffer for eight 128-sample render quanta", () => {
    const { processor, messages } = createProcessor();
    for (let index = 0; index < 7; index += 1) {
      processor.process([[new Float32Array(128).fill(index + 1)]], [[new Float32Array(128)]]);
    }
    expect(messages).toHaveLength(0);
    processor.process([[new Float32Array(128).fill(8)]], [[new Float32Array(128)]]);
    expect(messages).toHaveLength(1);
    expect(messages[0]?.samples).toHaveLength(1024);
    expect(messages[0]?.transferred).toBe(messages[0]?.samples.buffer);
    expect(messages[0]?.audioWorkletOutputAtMs).toBeTypeOf("number");
    expect(messages[0]).toMatchObject({ callbackCount: 8, postMessageCount: 1, allocationCount: 2 });
    expect(messages[0]?.samples[0]).toBe(1);
    expect(messages[0]?.samples[1023]).toBe(8);
  });

  it("keeps transfer count bounded during sustained dual-channel input", () => {
    const microphone = createProcessor();
    const system = createProcessor();
    const tenSecondsOfQuanta = Math.ceil((48_000 * 10) / 128);
    const quantum = new Float32Array(128).fill(0.1);
    const output = new Float32Array(128);
    for (let index = 0; index < tenSecondsOfQuanta; index += 1) {
      microphone.processor.process([[quantum]], [[output]]);
      system.processor.process([[quantum]], [[output]]);
    }
    const expectedPerChannel = Math.floor((tenSecondsOfQuanta * 128) / 1024);
    expect(microphone.messages).toHaveLength(expectedPerChannel);
    expect(system.messages).toHaveLength(expectedPerChannel);
    expect(microphone.messages.length + system.messages.length).toBeLessThanOrEqual(940);
  });
});
