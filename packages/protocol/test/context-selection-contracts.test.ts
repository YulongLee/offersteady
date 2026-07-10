import { describe, expect, it } from "vitest";
import type { ContextLevel, SelectionIntegrity, SessionContextSelection } from "../src/context.js";

const roundTrip = (value: SessionContextSelection) => JSON.parse(JSON.stringify(value)) as SessionContextSelection;

describe("optional context-selection contracts", () => {
  it.each([
    ["empty", { sessionId: "empty", resumeSourceId: null, jobDescriptionSourceId: null, knowledgeSourceIds: [], revision: 1, confirmedAtMs: 10 }],
    ["partial", { sessionId: "partial", resumeSourceId: null, jobDescriptionSourceId: "jd-1", knowledgeSourceIds: [], revision: 2, confirmedAtMs: 20 }],
    ["personalized", { sessionId: "full", resumeSourceId: "resume-1", jobDescriptionSourceId: "jd-1", knowledgeSourceIds: ["kb-1"], revision: 3, confirmedAtMs: 30 }],
  ] satisfies readonly [string, SessionContextSelection][])('round-trips a confirmed %s selection', (_name, selection) => {
    expect(roundTrip(selection)).toEqual(selection);
  });

  it("keeps classification derived for backward compatibility", () => {
    const integrity: SelectionIntegrity = "unconfirmed";
    const level: ContextLevel = "none";
    expect({ integrity, level }).toEqual({ integrity: "unconfirmed", level: "none" });
  });
});
