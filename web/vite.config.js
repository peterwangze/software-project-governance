import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev: Vite serves the UI on 5173 and proxies /api to the local Python
// governance API server on 5174. In production, `web/server.py` serves both
// the API and the built dist/ on a single port.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5174',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
});
