import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

import { validateProductionWebBuildEnvironment } from "./production-env-guard";

export default defineConfig(({ mode }) => {
  const publicEnv = loadEnv(mode, process.cwd(), "");
  validateProductionWebBuildEnvironment(mode, publicEnv);
  return {
    plugins: [
      react(),
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
