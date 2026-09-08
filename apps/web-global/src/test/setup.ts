import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

const storage = () => {
  const values = new Map<string, string>();
  return {
    get length() { return values.size; },
    clear: () => values.clear(),
    getItem: (key: string) => values.get(key) ?? null,
    key: (index: number) => [...values.keys()][index] ?? null,
    removeItem: (key: string) => { values.delete(key); },
    setItem: (key: string, value: string) => { values.set(key, String(value)); },
  } satisfies Storage;
};

Object.defineProperty(window, "localStorage", { configurable: true, value: storage() });
Object.defineProperty(window, "sessionStorage", { configurable: true, value: storage() });

afterEach(() => {
  cleanup();
  window.sessionStorage.clear();
  Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
});
