import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import runtimeErrorOverlay from "@replit/vite-plugin-runtime-error-modal";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");

  const gitpodUrl = process.env.GITPOD_WORKSPACE_URL;
  const allowedHosts: string[] = [];

  if (gitpodUrl) {
    try {
      const url = new URL(gitpodUrl);
      const baseHost = url.hostname;

      // Add common dev ports used in Gitpod/Vite
      const ports = [3000, 5173, 4173, 4321, 8080]; // You can add more here if needed

      ports.forEach(port => {
        allowedHosts.push(`${port}-${baseHost}`);
      });

    } catch (err) {
      console.warn("Invalid GITPOD_WORKSPACE_URL:", gitpodUrl);
    }
  }

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
      },
      allowedHosts
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

    ssr: {
      external: ["react", "react-dom"]
    }
  };
});