/**
 * Vite yapılandırması.
 *
 * Geliştirmede panel 5173'te, API 8080'de koşar; /api ve /worker çağrıları
 * sunucuya yönlendirilir. Üretimde derleme çıktısı Express'ten servis edilir.
 */
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath } from "node:url";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src/web", import.meta.url)) },
  },
  build: { outDir: "dist/web", emptyOutDir: true },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8080",
      "/worker": "http://127.0.0.1:8080",
    },
  },
});