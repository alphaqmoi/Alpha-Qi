// vite.ts

import { fileURLToPath } from "url";
import path from "path";
import dotenv from "dotenv";
import express, { type Express } from "express";
import fs from "fs";
import { createServer as createViteServer, createLogger } from "vite";
import react from "@vitejs/plugin-react"; // ✅ include React support
import { type Server } from "http";
import { nanoid } from "nanoid";

// Emulate __dirname in ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load .env variables
dotenv.config();

// Resolve client root folder
const clientRoot = path.resolve(__dirname, "../client");

// Create a Vite logger
const viteLogger = createLogger();

// Timestamped log function
export function log(message: string, source = "vite.ts") {
  const formattedTime = new Date().toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });
  console.log(`[${source}] ${formattedTime} - ${message}`);
}

export async function setupVite(app: Express, server: Server) {
  log(`clientRoot resolved to: ${clientRoot}`);

  const serverOptions = {
    middlewareMode: true,
    hmr: { server },
    allowedHosts: true,
  };

  const vite = await createViteServer({
    root: clientRoot,
    configFile: false,
    server: serverOptions,
    appType: "custom",
    plugins: [react()], // ✅ support JSX/TSX
    resolve: {
      alias: {
        '@': path.resolve(clientRoot, 'src'),
        '@shared': path.resolve(__dirname, '../shared'),
        '@assets': path.resolve(__dirname, '../attached_assets'),
      },
    },
    customLogger: {
      ...viteLogger,
      error: (msg, options) => {
        viteLogger.error(msg, options);
        process.exit(1);
      },
    },
  });

  // Use Vite middleware
  app.use(vite.middlewares);

  // Serve index.html via Vite with cache-busting
  app.use("*", async (req, res, next) => {
    const url = req.originalUrl;

    try {
      const clientTemplate = path.resolve(clientRoot, "index.html");
      log(`Serving index.html from: ${clientTemplate}`);

      let template = await fs.promises.readFile(clientTemplate, "utf-8");

      template = template.replace(
        `src="/src/main.tsx"`,
        `src="/src/main.tsx?v=${nanoid()}"`
      );

      const page = await vite.transformIndexHtml(url, template);
      res.status(200).set({ "Content-Type": "text/html" }).end(page);
    } catch (e) {
      vite.ssrFixStacktrace(e as Error);
      next(e);
    }
  });
}

export function serveStatic(app: Express) {
  const distPath = path.resolve(__dirname, "public");

  if (!fs.existsSync(distPath)) {
    throw new Error(
      `Could not find the build directory: ${distPath}, make sure to build the client first`
    );
  }

  app.use(express.static(distPath));

  app.use("*", (_req, res) => {
    res.sendFile(path.resolve(distPath, "index.html"));
  });
}
