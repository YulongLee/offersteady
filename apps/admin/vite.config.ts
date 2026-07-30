import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  build: { target: "chrome100" },
  server: { host: "127.0.0.1", port: 5180, strictPort: true },
  preview: { host: "127.0.0.1", port: 4180, strictPort: true },
});
