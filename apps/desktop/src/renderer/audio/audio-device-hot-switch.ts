import type { AudioSourceDescriptor } from "@offersteady/protocol";

export const AUDIO_DEVICE_CHANGE_DEBOUNCE_MS = 400;

export const reconcileMicrophoneSelection = (
  sources: readonly AudioSourceDescriptor[],
  currentId: string,
  preferredId?: string,
): string => {
  if (preferredId && sources.some(source => source.id === preferredId)) return preferredId;
  if (currentId && sources.some(source => source.id === currentId)) return currentId;
  const defaultSource = sources.find(
    source => source.id === "default" || source.label.toLowerCase().startsWith("default"),
  );
  return defaultSource?.id ?? sources[0]?.id ?? "default";
};

export interface DebouncedDeviceRefresh {
  readonly notify: () => void;
  readonly dispose: () => void;
}

export const createDebouncedDeviceRefresh = (
  refresh: () => void,
  delayMs = AUDIO_DEVICE_CHANGE_DEBOUNCE_MS,
): DebouncedDeviceRefresh => {
  let timer: number | null = null;
  return {
    notify: () => {
      if (timer !== null) window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        timer = null;
        refresh();
      }, delayMs);
    },
    dispose: () => {
      if (timer !== null) window.clearTimeout(timer);
      timer = null;
    },
  };
};

export class SerializedLatestSourceSwitch {
  private desiredSourceId: string;
  private appliedSourceId: string;
  private running: Promise<void> | null = null;

  constructor(initialSourceId: string) {
    this.desiredSourceId = initialSourceId;
    this.appliedSourceId = initialSourceId;
  }

  markApplied(sourceId: string): void {
    this.appliedSourceId = sourceId;
  }

  stage(sourceId: string): void {
    this.desiredSourceId = sourceId;
  }

  get desired(): string {
    return this.desiredSourceId;
  }

  request(sourceId: string, apply: (sourceId: string) => Promise<boolean>): Promise<void> {
    this.stage(sourceId);
    if (this.running) return this.running;
    const task = (async () => {
      while (this.appliedSourceId !== this.desiredSourceId) {
        const target = this.desiredSourceId;
        const applied = await apply(target);
        if (applied) {
          this.appliedSourceId = target;
        } else if (target === this.desiredSourceId) {
          break;
        }
      }
    })();
    this.running = task.finally(() => {
      this.running = null;
    });
    return this.running;
  }
}
