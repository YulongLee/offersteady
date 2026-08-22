import { describe, expect, it } from "vitest";

import {
  clearRememberedAdminPhone,
  isValidAdminPhone,
  normalizeAdminPhone,
  readRememberedAdminPhone,
  saveRememberedAdminPhone,
} from "./login-preferences";

function memoryStorage() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  };
}

describe("admin login phone preferences", () => {
  it("normalizes mainland phone input without broadening validation", () => {
    expect(normalizeAdminPhone("+86 197-2963-0316")).toBe("19729630316");
    expect(isValidAdminPhone("19729630316")).toBe(true);
    expect(isValidAdminPhone("1234")).toBe(false);
  });

  it("stores only a valid normalized phone and can remove it", () => {
    const storage = memoryStorage();
    saveRememberedAdminPhone("+86 197 2963 0316", storage);
    expect(readRememberedAdminPhone(storage)).toBe("19729630316");

    clearRememberedAdminPhone(storage);
    expect(readRememberedAdminPhone(storage)).toBe("");
  });

  it("ignores malformed persisted values", () => {
    const storage = memoryStorage();
    storage.setItem("offersteady.admin.remembered-phone", "not-a-phone");
    expect(readRememberedAdminPhone(storage)).toBe("");
  });
});
