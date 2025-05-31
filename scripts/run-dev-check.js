const { execSync } = require("child_process");
const os = require("os");
const path = require("path");

const isWindows = os.platform() === "win32";
const shell = isWindows ? "powershell.exe" : "bash";
const script = isWindows
  ? path.join("scripts", "dev-check.ps1")
  : path.join("scripts", "dev-check.sh");

try {
  execSync(`${shell} "${script}"`, { stdio: "inherit" });
} catch (e) {
  console.error("❌ Dev checks failed.");
  process.exit(1);
}
