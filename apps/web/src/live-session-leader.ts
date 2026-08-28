import type { RealtimeSessionUpdate } from "./domain";

type LeaderMessage = {
  readonly type: "probe" | "leader" | "release" | "state";
  readonly pageId: string;
  readonly epoch: number;
  readonly sentAt: number;
  readonly state?: RealtimeSessionUpdate;
};

type ChannelLike = Pick<BroadcastChannel, "postMessage" | "addEventListener" | "removeEventListener" | "close">;

export interface LiveSessionLeaderCallbacks {
  readonly onLeadershipChange: (leader: boolean) => void;
  readonly onState: (state: RealtimeSessionUpdate) => void;
}

export class LiveSessionLeaderCoordinator {
  private leader = false;
  private epoch = 0;
  private leaderPageId: string | null = null;
  private leaderEpoch = 0;
  private lastLeaderAt = 0;
  private eligible = true;
  private electionTimer: number | null = null;
  private heartbeatTimer: number | null = null;
  private watchdogTimer: number | null = null;
  private callbacks: LiveSessionLeaderCallbacks | null = null;

  constructor(
    private readonly channel: ChannelLike,
    private readonly pageId: string,
    private readonly now: () => number = Date.now,
  ) {}

  start(callbacks: LiveSessionLeaderCallbacks, eligible = true) {
    this.callbacks = callbacks;
    this.eligible = eligible;
    this.channel.addEventListener("message", this.onMessage as EventListener);
    if (this.eligible) this.requestElection();
    this.watchdogTimer = window.setInterval(() => {
      if (this.eligible && !this.leader && this.now() - this.lastLeaderAt > 5_000) this.becomeLeader();
    }, 1_000);
  }

  setEligible(eligible: boolean) {
    if (this.eligible === eligible) return;
    this.eligible = eligible;
    if (!eligible) {
      if (this.electionTimer !== null) {
        window.clearTimeout(this.electionTimer);
        this.electionTimer = null;
      }
      // A sole live page must keep its healthy network stream while the user
      // briefly switches to the interview app or companion. Releasing here
      // forced a full SSE recovery on every visibility transition and delayed
      // already-published first partials. A visible follower can still take
      // over immediately through the probe branch below.
      if (!this.leader && this.leaderPageId === this.pageId) this.leaderPageId = null;
      return;
    }
    if (this.leader) return;
    this.lastLeaderAt = 0;
    this.requestElection();
  }

  publishState(state: RealtimeSessionUpdate) {
    if (!this.leader) return;
    this.post("state", state);
  }

  isLeader() {
    return this.leader;
  }

  stop() {
    if (this.leader) this.post("release");
    this.setLeader(false);
    if (this.electionTimer !== null) window.clearTimeout(this.electionTimer);
    if (this.watchdogTimer !== null) window.clearInterval(this.watchdogTimer);
    this.channel.removeEventListener("message", this.onMessage as EventListener);
    this.channel.close();
    this.callbacks = null;
  }

  private readonly onMessage = (event: MessageEvent<LeaderMessage>) => {
    const message = event.data;
    if (!message || message.pageId === this.pageId) return;
    if (message.type === "probe") {
      if (this.leader && !this.eligible) {
        this.post("release");
        this.setLeader(false);
        if (this.leaderPageId === this.pageId) this.leaderPageId = null;
      } else if (this.eligible && this.leader) {
        this.post("leader");
      }
      return;
    }
    if (message.type === "release") {
      if (this.eligible && !this.leader && message.epoch >= this.leaderEpoch) {
        this.leaderPageId = null;
        this.leaderEpoch = message.epoch;
        this.lastLeaderAt = 0;
        this.becomeLeader();
      }
      return;
    }
    if (message.type === "leader") {
      if (this.eligible && this.leader && this.pageId < message.pageId) {
        this.post("leader");
        return;
      }
      if (!this.leader || message.pageId < this.pageId || message.epoch > this.epoch) {
        this.leaderPageId = message.pageId;
        this.leaderEpoch = message.epoch;
        this.lastLeaderAt = this.now();
        this.setLeader(false);
      }
      return;
    }
    if (message.type === "state") {
      if (message.pageId !== this.leaderPageId || message.epoch < this.leaderEpoch || !message.state) return;
      this.lastLeaderAt = this.now();
      this.callbacks?.onState(message.state);
    }
  };

  private becomeLeader() {
    if (!this.eligible) return;
    this.epoch = Math.max(this.epoch + 1, this.now());
    this.leaderPageId = this.pageId;
    this.leaderEpoch = this.epoch;
    this.lastLeaderAt = this.now();
    this.setLeader(true);
    this.post("leader");
    if (this.heartbeatTimer !== null) window.clearInterval(this.heartbeatTimer);
    this.heartbeatTimer = window.setInterval(() => this.post("leader"), 2_000);
  }

  private requestElection() {
    if (!this.eligible) return;
    this.post("probe");
    if (this.electionTimer !== null) window.clearTimeout(this.electionTimer);
    this.electionTimer = window.setTimeout(() => {
      this.electionTimer = null;
      if (this.eligible && this.now() - this.lastLeaderAt >= 120) this.becomeLeader();
    }, 120);
  }

  private setLeader(value: boolean) {
    if (this.leader === value) return;
    this.leader = value;
    if (!value && this.heartbeatTimer !== null) {
      window.clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    this.callbacks?.onLeadershipChange(value);
  }

  private post(type: LeaderMessage["type"], state?: RealtimeSessionUpdate) {
    this.channel.postMessage({
      type,
      pageId: this.pageId,
      epoch: this.epoch,
      sentAt: this.now(),
      ...(state ? { state } : {}),
    } satisfies LeaderMessage);
  }
}

export const createLiveSessionLeaderCoordinator = (channelName: string, pageId: string) => {
  if (typeof BroadcastChannel !== "function") return null;
  return new LiveSessionLeaderCoordinator(new BroadcastChannel(channelName), pageId);
};
