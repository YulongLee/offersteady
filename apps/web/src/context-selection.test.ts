import { describe, expect, it } from "vitest";
import { syntheticLibrarySources, syntheticState } from "./test-state";
import { contextLevel, reviseSelection, selectionSources, selectionValidity } from "./context-selection";

describe("per-interview context selection", () => {
  it("validates one ready resume, one ready JD and multiple knowledge items", () => {
    const selection = syntheticState.contextSelections.demo!;
    expect(selectionValidity(syntheticLibrarySources, selection)).toBe("valid");
    expect(selectionSources(syntheticLibrarySources, selection)).toHaveLength(4);
  });

  it("accepts confirmed empty and partial selections", () => {
    const base = syntheticState.contextSelections.demo!;
    const empty = { ...base, resumeSourceId: null, jobDescriptionSourceId: null, knowledgeSourceIds: [] };
    expect(selectionValidity(syntheticLibrarySources, empty)).toBe("valid");
    expect(contextLevel(empty)).toBe("none");
    expect(contextLevel({ ...empty, jobDescriptionSourceId: "jd-frontend" })).toBe("jd-only");
    expect(contextLevel({ ...empty, knowledgeSourceIds: ["kb-performance"] })).toBe("knowledge-only");
    expect(contextLevel({ ...empty, resumeSourceId: "resume-frontend" })).toBe("resume-only");
    expect(contextLevel({ ...empty, resumeSourceId: "resume-frontend", knowledgeSourceIds: ["kb-performance"] })).toBe("partial");
    expect(contextLevel({ ...empty, resumeSourceId: "resume-frontend", jobDescriptionSourceId: "jd-frontend" })).toBe("personalized");
  });

  it("distinguishes an unconfirmed backward-compatible selection", () => {
    expect(selectionValidity(syntheticLibrarySources, { sessionId: "old", resumeSourceId: null, jobDescriptionSourceId: null, knowledgeSourceIds: [], revision: 0, confirmedAtMs: null })).toBe("unconfirmed");
  });

  it("requires attention when a selected source is disabled", () => {
    const selection = { ...syntheticState.contextSelections.demo!, knowledgeSourceIds: ["kb-product"] };
    expect(selectionValidity(syntheticLibrarySources, selection)).toBe("attention-required");
  });

  it("increments revisions and deduplicates knowledge IDs", () => {
    const current = syntheticState.contextSelections.demo!;
    const revised = reviseSelection(current, { resumeSourceId: current.resumeSourceId, jobDescriptionSourceId: current.jobDescriptionSourceId, knowledgeSourceIds: ["kb-performance", "kb-performance"] }, 10);
    expect(revised.revision).toBe(current.revision + 1); expect(revised.knowledgeSourceIds).toEqual(["kb-performance"]); expect(revised.confirmedAtMs).toBe(10);
  });

  it("keeps independently confirmed empty and partial drafts isolated", () => {
    const empty = reviseSelection({ sessionId: "a", resumeSourceId: null, jobDescriptionSourceId: null, knowledgeSourceIds: [], revision: 0, confirmedAtMs: null }, { resumeSourceId: null, jobDescriptionSourceId: null, knowledgeSourceIds: [] }, 10);
    const partial = reviseSelection({ sessionId: "b", resumeSourceId: null, jobDescriptionSourceId: null, knowledgeSourceIds: [], revision: 0, confirmedAtMs: null }, { resumeSourceId: null, jobDescriptionSourceId: "jd-frontend", knowledgeSourceIds: [] }, 20);
    expect(empty.sessionId).toBe("a"); expect(contextLevel(empty)).toBe("none");
    expect(partial.sessionId).toBe("b"); expect(contextLevel(partial)).toBe("jd-only");
  });
});
