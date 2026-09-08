import { describe, expect, it } from "vitest";

import { adminViewsForEdition } from "./App";

const ids = (edition: "cn" | "global") => adminViewsForEdition(edition).map(view => view.id);

describe("edition-specific Admin modules", () => {
  it("exposes only applicable operations in Global Admin", () => {
    expect(ids("global")).toEqual([
      "dashboard",
      "server",
      "users",
      "globalMembers",
      "globalCommerce",
      "materials",
      "interviews",
      "audit",
      "admins",
    ]);
  });

  it("does not expose China-only commercial modules in Global Admin", () => {
    expect(ids("global")).not.toEqual(expect.arrayContaining([
      "promotion",
      "orders",
      "payments",
      "growth",
      "pricing",
      "redemptions",
    ]));
  });

  it("preserves the existing Chinese Admin module set", () => {
    expect(ids("cn")).toEqual([
      "dashboard",
      "server",
      "users",
      "promotion",
      "orders",
      "payments",
      "growth",
      "pricing",
      "redemptions",
      "materials",
      "interviews",
      "audit",
      "admins",
    ]);
  });
});
