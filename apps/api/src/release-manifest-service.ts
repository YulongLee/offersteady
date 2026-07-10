import type { DesktopReleaseEntry, DesktopReleaseManifest } from "@offersteady/protocol";

export class ReleaseManifestError extends Error { constructor(readonly code: "forbidden" | "invalid-release" | "not-found", message: string) { super(message); } }
export class ReleaseManifestService {
  private entries = new Map<string, DesktopReleaseEntry>();
  private version = 0;
  publish(role: "release-manager" | "support", entry: DesktopReleaseEntry) { if (role !== "release-manager") throw new ReleaseManifestError("forbidden", "没有发布权限"); this.validate(entry); this.entries.set(entry.id, entry); this.version += 1; return this.manifest(); }
  withdraw(role: "release-manager" | "support", id: string) { if (role !== "release-manager") throw new ReleaseManifestError("forbidden", "没有撤回权限"); const entry = this.entries.get(id); if (!entry) throw new ReleaseManifestError("not-found", "版本不存在"); const { downloadUrl: _removed, ...safe } = entry; this.entries.set(id, { ...safe, signingStatus: "withdrawn" }); this.version += 1; return this.manifest(); }
  manifest(nowMs = Date.now()): DesktopReleaseManifest { return { version: this.version, generatedAtMs: nowMs, entries: [...this.entries.values()].filter(item => item.signingStatus === "verified" && Boolean(item.downloadUrl)) }; }
  private validate(entry: DesktopReleaseEntry) { if (entry.signingStatus !== "verified" || !entry.downloadUrl || !/^[a-f0-9]{64}$/i.test(entry.sha256)) throw new ReleaseManifestError("invalid-release", "发布包未完成签名或校验"); if (entry.platform === "macos" && !entry.notarized) throw new ReleaseManifestError("invalid-release", "macOS 发布包尚未公证"); }
}
