#!/usr/bin/env node
import { execSync } from "child_process";

console.log("🎨 Formatting code across projects...");
["shared", "server", "frontend"].forEach(pkg => {
  execSync(`prettier --write ${pkg}/**/*.{ts,tsx,js,jsx,json,css,md}`, { stdio: "inherit" });
});
console.log("✅ Formatting complete.");
