Write-Host "📦 Checking TypeScript project references..."

$ErrorActionPreference = "Stop"

# Run TypeScript build for project references
tsc --build tsconfig.json

Write-Host "✅ Type-check passed for all projects."
