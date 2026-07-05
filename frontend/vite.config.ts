import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api/v1/extract": {
        target: "http://localhost:8005",
        changeOrigin: true,
      },
      "/api/v1/convert": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
      "/api/v1/analyze": {
        target: "http://localhost:8002",
        changeOrigin: true,
      },
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
