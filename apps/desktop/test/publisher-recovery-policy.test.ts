import { afterEach, describe, expect, it, vi } from "vitest";

import { ChannelForwardProgressGate, FreshTransportAckGate, publisherRecoveryDelayMs } from "../src/renderer/audio/publisher-recovery-policy";

describe("replacement publisher recovery policy", () => {
  const timers = {
    setTimeout: (handler: () => void, timeoutMs: number) => globalThis.setTimeout(handler, timeoutMs) as unknown as number,
    clearTimeout: (timer: number) => globalThis.clearTimeout(timer as unknown as ReturnType<typeof setTimeout>),
  };

  afterEach(() => vi.useRealTimers());

  it("completes only from the current replacement transport acknowledgement", async () => {
    vi.useFakeTimers();
    const gate = new FreshTransportAckGate<object>(timers);
    const staleTransport = {};
    const currentTransport = {};
    const result = gate.wait(currentTransport, 4_000);

    expect(gate.markMediaPending(currentTransport)).toBe(true);
    expect(gate.acknowledge(staleTransport)).toBe(false);
    expect(gate.acknowledge(currentTransport)).toBe(true);
    await expect(result).resolves.toBeUndefined();
  });

  it("fails a replacement attempt that never proves ACK progress", async () => {
    vi.useFakeTimers();
    const gate = new FreshTransportAckGate<object>(timers);
    const transport = {};
    const result = gate.wait(transport, 4_000);
    const expectation = expect(result).rejects.toThrow("replacement-publisher-ack-timeout");

    gate.markMediaPending(transport);
    await vi.advanceTimersByTimeAsync(4_000);
    await expectation;
  });

  it("keeps one replacement transport ready while its sources remain silent", async () => {
    vi.useFakeTimers();
    const gate = new FreshTransportAckGate<object>(timers);
    const transport = {};
    const result = gate.wait(transport, 4_000);
    let settled = false;
    void result.finally(() => { settled = true; });

    await vi.advanceTimersByTimeAsync(40_000);

    expect(gate.isWaitingFor(transport)).toBe(true);
    expect(settled).toBe(false);
    gate.acknowledge(transport);
    await expect(result).resolves.toBeUndefined();
  });

  it("supersedes one pending gate and bounds retry frequency without exhausting recovery", async () => {
    vi.useFakeTimers();
    const gate = new FreshTransportAckGate<object>(timers);
    const first = gate.wait({}, 4_000);
    const firstExpectation = expect(first).rejects.toThrow("replacement-publisher-superseded");
    const secondTransport = {};
    const second = gate.wait(secondTransport, 4_000);
    await firstExpectation;
    gate.acknowledge(secondTransport);
    await expect(second).resolves.toBeUndefined();

    expect([
      publisherRecoveryDelayMs(1),
      publisherRecoveryDelayMs(2),
      publisherRecoveryDelayMs(3),
      publisherRecoveryDelayMs(4),
      publisherRecoveryDelayMs(20),
    ]).toEqual([250, 500, 1_000, 2_000, 5_000]);
    expect(publisherRecoveryDelayMs(20, 999)).toBe(5_150);
  });

  it("requires independent progress only from channels that produced replacement media", () => {
    const gate = new ChannelForwardProgressGate<object>();
    const stale = {};
    const current = {};
    gate.activate(current);
    gate.markMediaProduced(current, "microphone");
    gate.markMediaProduced(current, "system");
    expect(gate.acknowledge(stale, "microphone")).toBe(false);
    expect(gate.acknowledge(current, "system")).toBe(true);
    expect(gate.pendingChannels(current)).toEqual(["microphone"]);
    expect(gate.allProducedChannelsAcknowledged(current)).toBe(false);
    gate.acknowledge(current, "microphone");
    expect(gate.allProducedChannelsAcknowledged(current)).toBe(true);

    const silentMicrophoneTransport = {};
    gate.activate(silentMicrophoneTransport);
    gate.markMediaProduced(silentMicrophoneTransport, "system");
    gate.acknowledge(silentMicrophoneTransport, "system");
    expect(gate.allProducedChannelsAcknowledged(silentMicrophoneTransport)).toBe(true);
  });
});
