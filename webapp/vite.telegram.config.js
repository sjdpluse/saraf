// Deploy the ORIGINAL React entrypoint (webapp/src/main.jsx) to Telegram native hosting.
// Railway retains its existing vite.config.js and /miniapp/ base unchanged.
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [react()],
  base: '/',
  publicDir: '../assets',
  define: { __SARAF_NATIVE__: JSON.stringify(true) },
  build: {
    outDir: fileURLToPath(new URL('../serverless-poc/dist/', import.meta.url)),
    emptyOutDir: true,
    assetsDir: 'assets',
  },
});
