import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {fileURLToPath} from 'node:url';

const fixtureAdapter = fileURLToPath(new URL('./fixture-app-adapter.ts', import.meta.url));
const fixtureAuth = fileURLToPath(new URL('./fixture-auth-client.ts', import.meta.url));

export default defineConfig({
  plugins: [{
    name: 'offersteady-global-device-story-fixtures',
    enforce: 'pre',
    resolveId(source, importer) {
      if (source === './app-adapter' && importer?.endsWith('/src/App.tsx')) return fixtureAdapter;
      if (source === './auth-client' && importer?.endsWith('/src/App.tsx')) return fixtureAuth;
      return null;
    },
  }, react()],
  resolve: {alias: [
    {find: '@offersteady/react-jsx-runtime-original', replacement: fileURLToPath(new URL('../../node_modules/react/jsx-runtime.js', import.meta.url))},
    {find: '@offersteady/react-jsx-dev-runtime-original', replacement: fileURLToPath(new URL('../../node_modules/react/jsx-dev-runtime.js', import.meta.url))},
    {find: /^react\/jsx-runtime$/, replacement: fileURLToPath(new URL('../../apps/web-global/src/global-jsx-runtime.ts', import.meta.url))},
    {find: /^react\/jsx-dev-runtime$/, replacement: fileURLToPath(new URL('../../apps/web-global/src/global-jsx-dev-runtime.ts', import.meta.url))},
  ]},
  server: {host: '127.0.0.1', port: 5191, strictPort: true},
});
