import { describe, expect, it } from "vitest";

import { readRuntimeConfig } from "./runtime-config";

describe("runtime config", () => {
  it("defaults to API-only localhost backend", () => {
    expect(readRuntimeConfig({})).toEqual({
      appEnv: "development",
      appVersion: "0.1.0",
      apiBaseUrl: "http://127.0.0.1:8000",
    });
  });

  it("keeps API-only runtime even if legacy fixture variables are present", () => {
    expect(
      readRuntimeConfig({
        VITE_APP_ENV: "production",
        VITE_APP_DATA_SOURCE: "fixture",
        VITE_API_BASE_URL: "http://localhost:8010/",
        VITE_PUBLIC_APP_VERSION: "1.2.3",
      } as Record<string, string>),
    ).toEqual({
      appEnv: "production",
      appVersion: "1.2.3",
      apiBaseUrl: "http://localhost:8010",
    });
  });

  it("normalizes an API-versioned backend URL to the backend root", () => {
    expect(readRuntimeConfig({ VITE_API_BASE_URL: "http://127.0.0.1:8000/api/v1/" }).apiBaseUrl).toBe("http://127.0.0.1:8000");
  });
});
