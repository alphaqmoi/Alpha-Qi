const { execSync } = require("child_process");

function setupHusky() {
  console.log("Setting up Husky Git hooks...");
  try {
    execSync("npx husky install", { stdio: "inherit" });
    execSync('npx husky add .husky/pre-commit "npm run lint"', {
      stdio: "inherit",
    });
    console.log("Husky setup completed.");
  } catch (err) {
    console.error("Failed to setup Husky", err);
  }
}

setupHusky();
