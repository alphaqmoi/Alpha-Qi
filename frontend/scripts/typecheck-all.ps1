Write-Host "🔍 Running typecheck for all packages..."

pnpm tsc -b frontend server shared
if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ Typecheck failed."
  exit 1
}

Write-Host "✅ Typecheck passed for all packages."
