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

          if (id.includes("react-datepicker")) {
            return "date-picker";
          }

          if (id.includes("react-select")) {
            return "select";
          }

          if (id.includes("@headlessui/react")) {
            return "headless-ui";
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
