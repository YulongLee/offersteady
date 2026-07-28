const defineValue = (target: object, property: PropertyKey, value: unknown) => {
  Object.defineProperty(target, property, {
    configurable: true,
    writable: true,
    value,
  });
};

export function installLegacyBrowserPolyfills() {
  if (typeof Array.prototype.at !== "function") {
    defineValue(Array.prototype, "at", function at<T>(this: readonly T[], index: number) {
      const normalizedIndex = Math.trunc(index) || 0;
      const resolvedIndex = normalizedIndex < 0 ? this.length + normalizedIndex : normalizedIndex;
      return resolvedIndex < 0 || resolvedIndex >= this.length ? undefined : this[resolvedIndex];
    });
  }

  if (typeof Object.hasOwn !== "function") {
    defineValue(Object, "hasOwn", (value: object, property: PropertyKey) =>
      Object.prototype.hasOwnProperty.call(value, property));
  }

  if (typeof globalThis.structuredClone !== "function") {
    defineValue(globalThis, "structuredClone", <T>(value: T): T =>
      JSON.parse(JSON.stringify(value)) as T);
  }

  if (globalThis.crypto && typeof globalThis.crypto.randomUUID !== "function") {
    defineValue(globalThis.crypto, "randomUUID", () => {
      const bytes = new Uint8Array(16);
      globalThis.crypto.getRandomValues(bytes);
      bytes[6] = (bytes[6]! & 0x0f) | 0x40;
      bytes[8] = (bytes[8]! & 0x3f) | 0x80;
      const hex = Array.from(bytes, byte => byte.toString(16).padStart(2, "0"));
      return `${hex.slice(0, 4).join("")}-${hex.slice(4, 6).join("")}-${hex.slice(6, 8).join("")}-${hex.slice(8, 10).join("")}-${hex.slice(10).join("")}`;
    });
  }
}

installLegacyBrowserPolyfills();
