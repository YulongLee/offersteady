import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig } from "vite";

const root = resolve(import.meta.dirname, "src/floating-preview");

export default defineConfig({
  root,
  envDir: false,
  publicDir: false,
  base: "./",
  plugins: [{
    name: "floating-site-styles",
    generateBundle() {
      this.emitFile({
        type: "asset",
        fileName: "online-site.css",
        source: readFileSync(resolve(root, "online-site.css"), "utf8"),
      });
    },
  }],
  build: {
    outDir: resolve(import.meta.dirname, "dist/floating-preview"),
    emptyOutDir: true,
    rollupOptions: { input: resolve(root, "interview.html") },
  },
});
