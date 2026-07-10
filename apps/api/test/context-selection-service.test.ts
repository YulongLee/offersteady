import { describe, expect, it } from "vitest";
import type { ContextLibrarySource } from "@offersteady/protocol";
import { ContextSelectionError, ContextSelectionService } from "../src/context-selection-service.js";

const sources: ContextLibrarySource[] = [
  { id: "resume-a", ownerUserId: "u1", kind: "resume", displayName: "前端简历", version: "v1", status: "ready", updatedAtMs: 1 },
  { id: "resume-b", ownerUserId: "u2", kind: "resume", displayName: "他人简历", version: "v1", status: "ready", updatedAtMs: 1 },
  { id: "jd-a", ownerUserId: "u1", kind: "jd", displayName: "前端 JD", version: "v1", status: "ready", updatedAtMs: 1 },
  { id: "kb-a", ownerUserId: "u1", kind: "knowledge", displayName: "性能治理", version: "v2", status: "ready", updatedAtMs: 1 },
  { id: "kb-b", ownerUserId: "u1", kind: "knowledge", displayName: "失效材料", version: "v1", status: "failed", updatedAtMs: 1 },
];

describe("ContextSelectionService", () => {
  const create = () => { const service = new ContextSelectionService(sources); service.registerSession("s1", "u1"); service.registerSession("s2", "u1"); return service; };

  it("persists isolated versioned selections", () => {
    const service = create();
    const first = service.confirm({ userId: "u1", sessionId: "s1", expectedRevision: 0, resumeSourceId: "resume-a", jobDescriptionSourceId: "jd-a", knowledgeSourceIds: ["kb-a", "kb-a"] }, 100);
    expect(first.revision).toBe(1); expect(first.knowledgeSourceIds).toEqual(["kb-a"]);
    expect(service.getSelection("u1", "s2").revision).toBe(0);
  });

  it("persists a confirmed empty allowlist without fallback", () => {
    const service = create();
    const empty = service.confirm({ userId: "u1", sessionId: "s1", expectedRevision: 0, resumeSourceId: null, jobDescriptionSourceId: null, knowledgeSourceIds: [] }, 100);
    expect(empty).toMatchObject({ revision: 1, confirmedAtMs: 100, resumeSourceId: null, jobDescriptionSourceId: null, knowledgeSourceIds: [] });
    expect(service.allowedSources("u1", "s1", 1)).toEqual([]);
    expect(service.provenance("u1", "s1", 1, ["resume-a", "jd-a"])).toEqual({ selectionRevision: 1, usedSources: [] });
  });

  it("persists partial selections and exact provenance", () => {
    const service = create();
    service.confirm({ userId: "u1", sessionId: "s1", expectedRevision: 0, resumeSourceId: null, jobDescriptionSourceId: "jd-a", knowledgeSourceIds: [] }, 100);
    expect(service.allowedSources("u1", "s1", 1).map(source => source.id)).toEqual(["jd-a"]);
    expect(service.provenance("u1", "s1", 1, ["jd-a"]).usedSources).toEqual([expect.objectContaining({ sourceId: "jd-a", sourceVersion: "v1", kind: "jd" })]);
  });

  it("rejects retrieval before an empty selection is confirmed", () => {
    expect(() => create().allowedSources("u1", "s1", 0)).toThrowError(expect.objectContaining({ code: "invalid-source" }));
  });

  it.each([
    ["wrong user", () => create().getSelection("u2", "s1"), "unauthorized"],
    ["cross-user source", () => create().confirm({ userId: "u1", sessionId: "s1", expectedRevision: 0, resumeSourceId: "resume-b", jobDescriptionSourceId: "jd-a", knowledgeSourceIds: [] }), "invalid-source"],
    ["failed source", () => create().confirm({ userId: "u1", sessionId: "s1", expectedRevision: 0, resumeSourceId: "resume-a", jobDescriptionSourceId: "jd-a", knowledgeSourceIds: ["kb-b"] }), "invalid-source"],
  ])("rejects %s", (_name, run, code) => expect(run).toThrowError(expect.objectContaining({ code })));

  it("rejects unselected retrieval and excludes irrelevant sources from provenance", () => {
    const service = create(); service.confirm({ userId: "u1", sessionId: "s1", expectedRevision: 0, resumeSourceId: "resume-a", jobDescriptionSourceId: "jd-a", knowledgeSourceIds: ["kb-a"] });
    expect(() => service.allowedSources("u1", "s1", 1, ["kb-b"])).toThrow(ContextSelectionError);
    expect(service.provenance("u1", "s1", 1, ["resume-a"]).usedSources.map(source => source.displayName)).toEqual(["前端简历"]);
  });

  it("invalidates deleted sources for future retrieval", () => {
    const service = create(); service.confirm({ userId: "u1", sessionId: "s1", expectedRevision: 0, resumeSourceId: "resume-a", jobDescriptionSourceId: "jd-a", knowledgeSourceIds: ["kb-a"] });
    service.setSourceStatus("kb-a", "deleted");
    expect(() => service.allowedSources("u1", "s1", 1)).toThrowError(expect.objectContaining({ code: "invalid-source" }));
  });
});
