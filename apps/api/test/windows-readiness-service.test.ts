import { describe, expect, it } from "vitest";
import type { ReadinessCheck } from "@offersteady/protocol";
import { WindowsReadinessService } from "../src/windows-readiness-service.js";
const checks: ReadinessCheck[] = ["signed-artifact", "install-lifecycle", "protocol", "identity", "pairing", "reconnect", "microphone", "system-audio", "physical-devices"];
describe("WindowsReadinessService", () => {
  it("does not claim support until every current check passes", () => { const service = new WindowsReadinessService(); checks.slice(0, -1).forEach((check, index) => service.update("release-manager", { check, passed: true, releaseVersion: "1", verifiedAtMs: index + 1, expiresAtMs: 100 })); expect(service.readiness("1", 50).status).toBe("not-ready"); service.update("release-manager", { check: "physical-devices", passed: true, releaseVersion: "1", verifiedAtMs: 10, expiresAtMs: 100 }); expect(service.readiness("1", 50).status).toBe("supported"); });
  it("expires and revokes support evidence and enforces roles", () => { const service = new WindowsReadinessService(); expect(() => service.update("support", { check: "protocol", passed: true, releaseVersion: "1", verifiedAtMs: 1, expiresAtMs: 2 })).toThrowError(expect.objectContaining({ code: "forbidden" })); checks.forEach(check => service.update("release-manager", { check, passed: true, releaseVersion: "1", verifiedAtMs: 1, expiresAtMs: 10 })); expect(service.readiness("1", 11).status).toBe("not-ready"); service.revoke("release-manager", "1"); expect(service.readiness("1", 2).status).toBe("revoked"); });
});
