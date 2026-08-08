import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base: '/miniapp/' چون FastAPI (api.py) این پوشه را دقیقاً روی همین مسیر mount می‌کند.
export default defineConfig({
  plugins: [react()],
  base: "/miniapp/",
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
