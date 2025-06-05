# Set strict error handling
$ErrorActionPreference = "Stop"

Write-Host "🧹 Cleaning previous builds..."
tsc --build --clean

Write-Host "📦 Checking TypeScript project references..."
tsc --build tsconfig.json

# Optional: Include linting if desired
Write-Host "🔍 Running ESLint..."
npx eslint . --ext .ts,.tsx

Write-Host "✅ Type-check and lint passed for all projects."
