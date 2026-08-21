import { describe, expect, it } from "vitest";

import { validateProductionWebBuildEnvironment } from "./production-env-guard";

describe("production Web build environment guard", () => {
  it("accepts an explicit same-origin production API", () => {
    expect(() => validateProductionWebBuildEnvironment("production", {
      VITE_APP_ENV: "production",
      VITE_API_BASE_URL: "/",
      VITE_PUBLIC_APP_VERSION: "0.1.0",
    })).not.toThrow();
  });

  it("accepts an explicit HTTPS production API", () => {
    expect(() => validateProductionWebBuildEnvironment("production", {
      VITE_APP_ENV: "production",
      VITE_API_BASE_URL: "https://mianshiwen.cn",
      VITE_PUBLIC_APP_VERSION: "0.1.0",
    })).not.toThrow();
  });

  it.each([undefined, "", "http://127.0.0.1:8000", "http://localhost:8000"])(
    "rejects unsafe production API base %s",
    apiBaseUrl => {
      expect(() => validateProductionWebBuildEnvironment("production", {
        VITE_APP_ENV: "production",
        VITE_API_BASE_URL: apiBaseUrl,
        VITE_PUBLIC_APP_VERSION: "0.1.0",
      })).toThrow();
    },
  );

  it("does not constrain the development server", () => {
    expect(() => validateProductionWebBuildEnvironment("development", {})).not.toThrow();
  });
});
