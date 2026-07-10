import { beforeEach, describe, expect, it, vi } from "vitest";

import { authClient } from "./auth-client";

describe("auth client", () => {
  beforeEach(() => {
    const store = new Map<string, string>();
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: {
        getItem: vi.fn((key: string) => store.get(key) ?? null),
        setItem: vi.fn((key: string, value: string) => store.set(key, value)),
        removeItem: vi.fn((key: string) => store.delete(key)),
      },
    });
  });

  it("does not silently assign the prototype admin account when no session exists", () => {
    expect(authClient.readStoredAccount()).toBeNull();
    expect(authClient.readStoredSession()).toBeNull();
  });
});
