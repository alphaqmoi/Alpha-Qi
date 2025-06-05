import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import runtimeErrorOverlay from "@replit/vite-plugin-runtime-error-modal";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");

  return {
    root: path.resolve(__dirname, "frontend"),

    plugins: [
      react(),
      runtimeErrorOverlay()
    ],

    resolve: {
      alias: {
        "@": path.resolve(__dirname, "frontend"),
        "@shared": path.resolve(__dirname, "shared"),
        "@assets": path.resolve(__dirname, "attached_assets")
      },
      extensions: [".js", ".ts", ".jsx", ".tsx", ".json"]
    },

    define: {
      "process.env": env
    },

    server: {
      port: 3000,
      host: true,
      strictPort: true,
      watch: {
        usePolling: true
      }
    },

    build: {
      outDir: path.resolve(__dirname, "server/public"),
      emptyOutDir: true
    },

    optimizeDeps: {
      include: ["@/components/ui/use-toast"]
    },

    esbuild: {
      jsxInject: `import React from 'react'`,
      loader: {
        ".js": "jsx",
        ".ts": "ts",
        ".tsx": "tsx"
      }
    },

    // Optional SSR support for hybrid rendering
    ssr: {
      external: ["react", "react-dom"]
    }
  };
});
