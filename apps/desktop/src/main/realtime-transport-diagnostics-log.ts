import { appendFile, mkdir, rename, rm, stat } from "node:fs/promises";
import path from "node:path";

const MAX_LOG_BYTES = 5 * 1024 * 1024;

export class RealtimeTransportDiagnosticsLog {
  readonly path: string;
  private pending: Promise<void> = Promise.resolve();

  constructor(userDataDirectory: string) {
    this.path = path.join(userDataDirectory, "realtime-audio-transport-diagnostics.ndjson");
  }

  append(snapshot: Record<string, unknown>): void {
    this.pending = this.pending.then(async () => {
      await mkdir(path.dirname(this.path), { recursive: true });
      const currentSize = await stat(this.path).then(value => value.size).catch(() => 0);
      if (currentSize >= MAX_LOG_BYTES) {
        const previousPath = `${this.path}.previous`;
        await rm(previousPath, { force: true });
        await rename(this.path, previousPath).catch(() => undefined);
      }
      await appendFile(this.path, `${JSON.stringify(snapshot)}\n`, { encoding: "utf8", mode: 0o600 });
    }).catch(error => {
      console.warn("[realtime-audio-transport-diagnostics] local log failed", error);
    });
  }
}
