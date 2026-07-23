import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/wp-content/plugins/notebooklm-py/dist/',
  build: {
    manifest: true,
    outDir: 'dist',
  },
  server: {
    port: 3000,
    host: true
  }
});
