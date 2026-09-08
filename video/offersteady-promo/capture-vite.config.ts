import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {fileURLToPath} from 'node:url';

const fixtureAdapter = fileURLToPath(new URL('./fixture-app-adapter.ts', import.meta.url));
const fixtureAuth = fileURLToPath(new URL('./fixture-auth-client.ts', import.meta.url));

export default defineConfig({
  plugins: [
    {
      name: 'offersteady-promo-fixture-adapter',
      enforce: 'pre',
      resolveId(source, importer) {
        if (source === './app-adapter' && importer?.endsWith('/src/App.tsx')) return fixtureAdapter;
        if (source === './auth-client' && importer?.endsWith('/src/App.tsx')) return fixtureAuth;
        return null;
      },
    },
    react(),
  ],
  server: {host: '127.0.0.1', port: 5181, strictPort: true},
});
