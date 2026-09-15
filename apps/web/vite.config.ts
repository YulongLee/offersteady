import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { readFileSync } from "node:fs";
import { loadProductionPricing, renderPricing } from "./pricing-static.mjs";

import { validateProductionWebBuildEnvironment } from "./production-env-guard";
import { legalStaticHtml } from "./legal-static";

export default defineConfig(({ mode }) => {
  const publicEnv = loadEnv(mode, process.cwd(), "");
  validateProductionWebBuildEnvironment(mode, publicEnv);
  return {
    plugins: [
      react(),
      {
        name: "cn-production-pricing-static",
        apply: "build",
        async generateBundle() {
          const template = readFileSync(new URL("./public/seo/pricing.html", import.meta.url), "utf8");
          const pricing = await loadProductionPricing();
          this.emitFile({ type: "asset", fileName: "seo/pricing.html", source: renderPricing(template, pricing) });
        },
      },
      {
        name: "existing-legal-static-documents",
        apply: "build",
        enforce: "post",
        generateBundle(_options, bundle) {
          const homepage = bundle["index.html"];
          if (!homepage || homepage.type !== "asset") throw new Error("Missing homepage build output");
          for (const kind of ["terms", "privacy"] as const) this.emitFile({ type: "asset", fileName: `${kind}.html`, source: legalStaticHtml(String(homepage.source), kind) });
        },
      },
      {
        name: "offersteady-production-build-manifest",
        apply: "build",
        generateBundle() {
          if (mode !== "production") return;
          this.emitFile({
            type: "asset",
            fileName: "offersteady-build.json",
            source: JSON.stringify({
              appEnv: publicEnv.VITE_APP_ENV,
              apiBaseUrl: publicEnv.VITE_API_BASE_URL,
              appVersion: publicEnv.VITE_PUBLIC_APP_VERSION,
            }),
          });
        },
      },
    ],
    resolve: {
      alias: mode === "test" ? {
        "./route-components": fileURLToPath(new URL("./src/route-components.eager.ts", import.meta.url)),
      } : {},
    },
    build: {
      target: "chrome86",
      rollupOptions: {
        input: {
          main: resolve(import.meta.dirname, "index.html"),
          guide: resolve(import.meta.dirname, "guide.html"),
        },
      },
    },
    server: {
      host: "127.0.0.1",
      port: 5173,
      strictPort: true,
      // Keep local preview requests same-origin so the development browser can
      // reach the local API without requiring production CORS configuration.
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: false,
        },
      },
    },
    preview: {
      host: "127.0.0.1",
      port: 4173,
      strictPort: true,
    },
    test: {
      environment: "jsdom",
      setupFiles: "./src/test/setup.ts",
    },
  };
});
