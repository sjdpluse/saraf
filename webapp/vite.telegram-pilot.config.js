// Dedicated read-only build; does not change the original Railway production build.
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const here = new URL(".", import.meta.url);
const pathOf = relative => fileURLToPath(new URL(relative, here));

export default defineConfig({
  root: pathOf("./telegram-pilot/"),
  plugins: [react()],
  base: "/",
  publicDir: pathOf("../assets/"),
  build: {
    outDir: pathOf("../serverless-poc/react-dist/"),
    emptyOutDir: true,
    assetsDir: "assets",
  },
});
