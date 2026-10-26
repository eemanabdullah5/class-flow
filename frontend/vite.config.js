import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // The browser only ever talks to localhost:5173. Vite forwards anything
    // starting with /api to the FastAPI backend, so no CORS setup is needed.
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom", // a pretend browser for tests
    setupFiles: "./src/test-setup.js",
  },
});
