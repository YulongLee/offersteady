import { afterEach, describe, expect, it } from "vitest";

import { installLegacyBrowserPolyfills } from "./legacy-browser-polyfills";

const descriptors = {
  arrayAt: Object.getOwnPropertyDescriptor(Array.prototype, "at"),
  hasOwn: Object.getOwnPropertyDescriptor(Object, "hasOwn"),
  structuredClone: Object.getOwnPropertyDescriptor(globalThis, "structuredClone"),
};

const restore = (target: object, property: PropertyKey, descriptor: PropertyDescriptor | undefined) => {
  if (descriptor) Object.defineProperty(target, property, descriptor);
  else Reflect.deleteProperty(target, property);
};

afterEach(() => {
  restore(Array.prototype, "at", descriptors.arrayAt);
  restore(Object, "hasOwn", descriptors.hasOwn);
  restore(globalThis, "structuredClone", descriptors.structuredClone);
});

describe("legacy browser compatibility", () => {
  it("restores APIs required by the live interview on Chrome 86", () => {
    Reflect.deleteProperty(Array.prototype, "at");
    Reflect.deleteProperty(Object, "hasOwn");
    Reflect.deleteProperty(globalThis, "structuredClone");

    installLegacyBrowserPolyfills();

    expect([1, 2, 3].at(-1)).toBe(3);
    expect(Object.hasOwn({ ready: true }, "ready")).toBe(true);
    expect(structuredClone({ sessionId: "session-current" })).toEqual({
      sessionId: "session-current",
    });
  });
});
