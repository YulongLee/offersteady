import { describe, expect, it } from "vitest";

import { foundationFeatureAreas, type FoundationIndexResponse, type PlaceholderOperationResponse } from "../src/foundation";

describe("foundation contracts", () => {
  it("covers the reserved phase-one feature areas", () => {
    expect(foundationFeatureAreas).toEqual([
      "session",
      "authentication",
      "resume",
      "job-description",
      "knowledge",
      "live-answer",
      "realtime-speech",
      "screenshot-answer",
      "billing",
    ]);
  });

  it("allows backend foundation responses to remain structured", () => {
    const index: FoundationIndexResponse = {
      service: "OfferSteady Backend",
      apiPrefix: "/api/v1",
      prototypeMode: "placeholder",
      modules: [
        {
          feature: "resume",
          owningApp: "apps/backend",
          routePrefix: "/api/v1/resume",
          mode: "placeholder",
          notes: "Reserved for later resume upload implementation.",
        },
      ],
    };
    const placeholder: PlaceholderOperationResponse<"live-answer"> = {
      status: "placeholder",
      feature: "live-answer",
      action: "start",
      message: "Reserved for a later implementation phase.",
    };
    expect(index.modules[0]?.feature).toBe("resume");
    expect(placeholder.feature).toBe("live-answer");
  });
});
