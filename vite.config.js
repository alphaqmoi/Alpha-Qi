// vite.config.js
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import runtimeErrorOverlay from "@replit/vite-plugin-runtime-error-modal";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");

  return {
    root: path.resolve(__dirname, "frontend"),
    plugins: [react(), runtimeErrorOverlay()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "frontend", "src"),
        "@shared": path.resolve(__dirname, "shared"),
        "@assets": path.resolve(__dirname, "attached_assets"),
      },
    },
    esbuild: {
      loader: "jsx", // <--- Tells esbuild to treat .js files as JSX
      include: /src\/.*\.js$/, // Apply to JS files in your src/
    },
    server: {
      watch: {
        usePolling: true,
      },
      port: 3000,
      strictPort: true,
      host: true,
    },
    build: {
      outDir: path.resolve(__dirname, "server", "public"),
      emptyOutDir: true,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes("node_modules")) {
              return id.toString().split("node_modules/")[1].split("/")[0];
            }
          },
        },
      },
    },
  };
});
