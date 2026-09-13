import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  envDir: "..",
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/health": "http://127.0.0.1:8000",
      "/disclaimer": "http://127.0.0.1:8000",
      "/me": "http://127.0.0.1:8000",
      "/cases": "http://127.0.0.1:8000",
      "/prefill": "http://127.0.0.1:8000",
      "/attorneys": "http://127.0.0.1:8000",
      "/consults": "http://127.0.0.1:8000",
      "/admin": "http://127.0.0.1:8000",
      "/chat": "http://127.0.0.1:8000",
      "/alerts": "http://127.0.0.1:8000",
    },
  },
});
