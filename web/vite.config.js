import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev: Vite serves the UI on 5173 and proxies /api to the local Python
// governance API server on 5174. In production, `web/server.py` serves both
// the API and the built dist/ on a single port.
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'governance-api',
      apply: 'serve',
      config(config) {
        const apiPort = config.server.port + 1;
        return { server: { proxy: { '/api': `http://127.0.0.1:${apiPort}` } } };
      },
    },
  ],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
  },
  build: {
    outDir: 'dist',
  },
});
