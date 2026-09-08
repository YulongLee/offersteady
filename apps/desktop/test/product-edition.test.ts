import { describe, expect, it } from "vitest";

import { resolveDesktopProductEdition } from "../src/main/product-edition";

describe("desktop product edition", () => {
  it("uses the immutable packaged Global runtime marker during early Electron startup", () => {
    expect(resolveDesktopProductEdition({
      hasPackagedGlobalRuntimeConfig: true,
      applicationName: "@offersteady/desktop",
    })).toBe("global");
  });

  it("keeps a packaged Chinese companion domestic when the Global marker is absent", () => {
    expect(resolveDesktopProductEdition({
      hasPackagedGlobalRuntimeConfig: false,
      applicationName: "@offersteady/desktop",
    })).toBe("domestic");
  });

  it("supports the explicit Global development profile", () => {
    expect(resolveDesktopProductEdition({
      explicitEdition: "global",
      hasPackagedGlobalRuntimeConfig: false,
      applicationName: "@offersteady/desktop",
    })).toBe("global");
  });
});
