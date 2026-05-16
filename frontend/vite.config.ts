import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) {
            return undefined;
          }

          if (id.includes("@mui/") || id.includes("@emotion/")) {
            return "mui";
          }

          if (id.includes("@tanstack/react-query")) {
            return "query";
          }
        },
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": "http://localhost:8080",
      "/media": "http://localhost:8080",
    },
  },
});
