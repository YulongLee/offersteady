import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const globalEdition = process.env.OFFERSTEADY_PRODUCT_EDITION === "global";

export default defineConfig({
  root: resolve(import.meta.dirname, "src/renderer"),
  base: "./",
  plugins: [
    react(),
    ...(globalEdition ? [{
      name: "offersteady-global-companion-html",
      transformIndexHtml(html: string) {
        return html.replace("<title>面试稳伴随程序</title>", "<title>OfferSteady Companion</title>");
      },
    }] : []),
  ],
  ...(globalEdition ? { resolve: {
    alias: [
      { find: "@offersteady/desktop-react-jsx-runtime-original", replacement: fileURLToPath(new URL("../../node_modules/react/jsx-runtime.js", import.meta.url)) },
      { find: "@offersteady/desktop-react-jsx-dev-runtime-original", replacement: fileURLToPath(new URL("../../node_modules/react/jsx-dev-runtime.js", import.meta.url)) },
      { find: /^react\/jsx-runtime$/, replacement: fileURLToPath(new URL("./src/renderer/global-jsx-runtime.ts", import.meta.url)) },
      { find: /^react\/jsx-dev-runtime$/, replacement: fileURLToPath(new URL("./src/renderer/global-jsx-dev-runtime.ts", import.meta.url)) },
    ],
  } } : {}),
  build: {
    outDir: resolve(import.meta.dirname, "dist/renderer"),
    emptyOutDir: true,
  },
  test: {
    root: import.meta.dirname,
    environment: "node",
    include: ["test/**/*.test.ts"],
  },
});
