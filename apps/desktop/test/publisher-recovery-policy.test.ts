import { afterEach, describe, expect, it, vi } from "vitest";

import { FreshTransportAckGate, ReplacementPublisherBudget } from "../src/renderer/audio/publisher-recovery-policy";

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

  it("supersedes one pending gate and bounds publisher creation until delivery drains", async () => {
    vi.useFakeTimers();
    const gate = new FreshTransportAckGate<object>(timers);
    const first = gate.wait({}, 4_000);
    const firstExpectation = expect(first).rejects.toThrow("replacement-publisher-superseded");
    const secondTransport = {};
    const second = gate.wait(secondTransport, 4_000);
    await firstExpectation;
    gate.acknowledge(secondTransport);
    await expect(second).resolves.toBeUndefined();

    const budget = new ReplacementPublisherBudget(3);
    expect([budget.claimAttempt(), budget.claimAttempt(), budget.claimAttempt(), budget.claimAttempt()]).toEqual([true, true, true, false]);
    budget.recordAcknowledgement(true);
    expect(budget.claimAttempt()).toBe(false);
    budget.recordAcknowledgement(false);
    expect(budget.claimAttempt()).toBe(true);
  });
});
