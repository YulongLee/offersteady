import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {fileURLToPath} from 'node:url';

export default defineConfig({
  plugins: [{
    name: 'offersteady-global-companion-fixture',
    enforce: 'pre',
    resolveId(source) {
      if (source === './audio/local-source-monitor') return fileURLToPath(new URL('./monitor-fixture.ts', import.meta.url));
      return null;
    },
  }, react()],
  resolve: {alias: [
    {find: '@offersteady/desktop-react-jsx-runtime-original', replacement: fileURLToPath(new URL('../../node_modules/react/jsx-runtime.js', import.meta.url))},
    {find: '@offersteady/desktop-react-jsx-dev-runtime-original', replacement: fileURLToPath(new URL('../../node_modules/react/jsx-dev-runtime.js', import.meta.url))},
    {find: /^react\/jsx-runtime$/, replacement: fileURLToPath(new URL('../../apps/desktop/src/renderer/global-jsx-runtime.ts', import.meta.url))},
    {find: /^react\/jsx-dev-runtime$/, replacement: fileURLToPath(new URL('../../apps/desktop/src/renderer/global-jsx-dev-runtime.ts', import.meta.url))},
  ]},
  server: {host: '127.0.0.1', port: 5192, strictPort: true},
});
