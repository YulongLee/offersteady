import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import publicReviewCatalogue from "./src/public-review-pages.json";

import { validateProductionWebBuildEnvironment } from "./production-env-guard";

export default defineConfig(({ mode }) => {
  const publicEnv = loadEnv(mode, process.cwd(), "");
  validateProductionWebBuildEnvironment(mode, publicEnv);
  return {
    plugins: [
      react(),
      {
        name: "offersteady-global-clean-public-routes",
        configureServer(server) {
          server.middlewares.use((request, _response, next) => {
            if (request.url && publicReviewCatalogue.pages.some(page => request.url === `/${page.slug}`)) request.url += "/";
            next();
          });
        },
        configurePreviewServer(server) {
          server.middlewares.use((request, _response, next) => {
            if (request.url && publicReviewCatalogue.pages.some(page => request.url === `/${page.slug}`)) request.url += "/";
            next();
          });
        },
      },
      {
        name: "offersteady-global-production-build-manifest",
        apply: "build",
        generateBundle() {
          if (mode !== "production") return;
          this.emitFile({
            type: "asset",
            fileName: "offersteady-global-build.json",
            source: JSON.stringify({
              appEnv: publicEnv.VITE_APP_ENV,
              apiBaseUrl: publicEnv.VITE_API_BASE_URL,
              appVersion: publicEnv.VITE_PUBLIC_APP_VERSION,
              productEdition: "global",
              locale: publicEnv.VITE_GLOBAL_LOCALE || "en-US",
              commerceEnabled: publicEnv.VITE_GLOBAL_COMMERCE_ENABLED === "true",
              commerceProvider: publicEnv.VITE_GLOBAL_COMMERCE_PROVIDER || "none",
            }),
          });
        },
      },
    ],
    resolve: {
      alias: [
        { find: "@offersteady/react-jsx-runtime-original", replacement: fileURLToPath(new URL("../../node_modules/react/jsx-runtime.js", import.meta.url)) },
        { find: "@offersteady/react-jsx-dev-runtime-original", replacement: fileURLToPath(new URL("../../node_modules/react/jsx-dev-runtime.js", import.meta.url)) },
        { find: /^react\/jsx-runtime$/, replacement: fileURLToPath(new URL("./src/global-jsx-runtime.ts", import.meta.url)) },
        { find: /^react\/jsx-dev-runtime$/, replacement: fileURLToPath(new URL("./src/global-jsx-dev-runtime.ts", import.meta.url)) },
        ...(mode === "test" ? [{ find: "./route-components", replacement: fileURLToPath(new URL("./src/route-components.eager.ts", import.meta.url)) }] : []),
      ],
    },
    build: {
      target: "chrome86",
      rollupOptions: {
        input: {
          main: resolve(import.meta.dirname, "index.html"),
          ...Object.fromEntries(publicReviewCatalogue.pages.map(page => [page.slug, resolve(import.meta.dirname, page.slug, "index.html")])),
        },
      },
    },
    server: {
      host: "127.0.0.1",
      port: 5273,
      strictPort: true,
    },
    preview: {
      host: "127.0.0.1",
      port: 4273,
      strictPort: true,
    },
    test: {
      environment: "jsdom",
      setupFiles: "./src/test/setup.ts",
    },
  };
});
