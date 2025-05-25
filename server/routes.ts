import { Express } from "express";

export async function registerRoutes(app: Express) {
  // Example route
  app.get("/api/health", (_req, res) => {
    res.json({ status: "ok" });
  });

  // Return the app's underlying HTTP server (for Vite integration)
  // If you use app.listen elsewhere, you may need to adjust this
  return app;
}
