import { afterEach, describe, expect, it, vi } from "vitest";

import type { RealtimeSessionUpdate } from "./domain";
import { LiveSessionLeaderCoordinator } from "./live-session-leader";

class FakeBus {
  readonly channels = new Set<FakeChannel>();
  channel() {
    const channel = new FakeChannel(this);
    this.channels.add(channel);
    return channel;
  }
  send(sender: FakeChannel, data: unknown) {
    for (const channel of this.channels) if (channel !== sender) channel.deliver(data);
  }
}

class FakeChannel {
  private readonly listeners = new Set<EventListener>();
  constructor(private readonly bus: FakeBus) {}
  postMessage(data: unknown) { this.bus.send(this, data); }
  addEventListener(_type: string, listener: EventListener) { this.listeners.add(listener); }
  removeEventListener(_type: string, listener: EventListener) { this.listeners.delete(listener); }
  close() { this.bus.channels.delete(this); }
  deliver(data: unknown) { for (const listener of this.listeners) listener({ data } as MessageEvent); }
}

afterEach(() => vi.useRealTimers());

describe("live session leader coordination", () => {
  const update: RealtimeSessionUpdate = {
    speaker: { mode: "dual-channel", transcripts: [], pendingQuestion: null, degradation: null, runtimeNotice: null },
  };

  it("elects one leader, relays state, and transfers leadership after release", () => {
    vi.useFakeTimers();
    let now = 1_000;
    const bus = new FakeBus();
    const firstStates: RealtimeSessionUpdate[] = [];
    const secondStates: RealtimeSessionUpdate[] = [];
    const firstLeadership: boolean[] = [];
    const secondLeadership: boolean[] = [];
    const first = new LiveSessionLeaderCoordinator(bus.channel(), "page-a", () => now);
    const second = new LiveSessionLeaderCoordinator(bus.channel(), "page-b", () => now);
    first.start({ onLeadershipChange: value => firstLeadership.push(value), onState: state => firstStates.push(state) });
    second.start({ onLeadershipChange: value => secondLeadership.push(value), onState: state => secondStates.push(state) });
    vi.advanceTimersByTime(121);

    expect(Number(first.isLeader()) + Number(second.isLeader())).toBe(1);
    const leader = first.isLeader() ? first : second;
    const followerStates = first.isLeader() ? secondStates : firstStates;
    leader.publishState(update);
    expect(followerStates).toHaveLength(1);

    leader.stop();
    now += 6_000;
    vi.advanceTimersByTime(6_000);
    const follower = first.isLeader() ? first : second;
    expect(follower.isLeader()).toBe(true);
    follower.stop();
    expect(firstLeadership.length + secondLeadership.length).toBeGreaterThanOrEqual(2);
  });

  it("does not accept stale state from a non-leader", () => {
    vi.useFakeTimers();
    const bus = new FakeBus();
    const states: RealtimeSessionUpdate[] = [];
    const first = new LiveSessionLeaderCoordinator(bus.channel(), "page-a", () => 1_000);
    const secondChannel = bus.channel();
    first.start({ onLeadershipChange: () => undefined, onState: state => states.push(state) });
    vi.advanceTimersByTime(121);
    secondChannel.postMessage({ type: "state", pageId: "stale", epoch: 0, sentAt: 1, state: update });
    expect(states).toEqual([]);
    first.stop();
    secondChannel.close();
  });

  it("releases a hidden leader and immediately transfers ownership to an eligible follower", () => {
    vi.useFakeTimers();
    let now = 1_000;
    const bus = new FakeBus();
    const first = new LiveSessionLeaderCoordinator(bus.channel(), "page-a", () => now);
    const second = new LiveSessionLeaderCoordinator(bus.channel(), "page-b", () => now);
    first.start({ onLeadershipChange: () => undefined, onState: () => undefined });
    second.start({ onLeadershipChange: () => undefined, onState: () => undefined });
    vi.advanceTimersByTime(121);
    const leader = first.isLeader() ? first : second;
    const follower = first.isLeader() ? second : first;

    leader.setEligible(false);

    expect(leader.isLeader()).toBe(false);
    expect(follower.isLeader()).toBe(true);
    leader.stop();
    follower.stop();
  });

  it("keeps an ineligible page from taking leadership until it becomes visible", () => {
    vi.useFakeTimers();
    let now = 1_000;
    const bus = new FakeBus();
    const hidden = new LiveSessionLeaderCoordinator(bus.channel(), "page-hidden", () => now);
    hidden.start({ onLeadershipChange: () => undefined, onState: () => undefined }, false);

    now += 6_000;
    vi.advanceTimersByTime(6_000);
    expect(hidden.isLeader()).toBe(false);

    hidden.setEligible(true);
    vi.advanceTimersByTime(121);
    expect(hidden.isLeader()).toBe(true);
    hidden.stop();
  });

  it("clears election and heartbeat timers when stopped", () => {
    vi.useFakeTimers();
    const bus = new FakeBus();
    const coordinator = new LiveSessionLeaderCoordinator(bus.channel(), "page-a", () => 1_000);
    coordinator.start({ onLeadershipChange: () => undefined, onState: () => undefined });
    vi.advanceTimersByTime(121);
    expect(coordinator.isLeader()).toBe(true);

    coordinator.stop();
    expect(coordinator.isLeader()).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
  });
});
