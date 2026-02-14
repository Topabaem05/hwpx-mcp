import path from "node:path";

import { defineConfig } from "vite";

export default defineConfig({
  root: path.join(__dirname, "renderer"),
  base: "./",
  server: {
    port: 5173,
    strictPort: true,
  },
  build: {
    target: "chrome120",
    outDir: path.join(__dirname, "dist-renderer"),
    emptyOutDir: true,
  },
});
