Write-Host "🚀 Running full DevQmoi workspace checks..."

Write-Host "🔧 Type-checking all TS projects..."
pnpm tsc -b
if ($LASTEXITCODE -ne 0) {
  Write-Error "❌ Type-check failed."
  exit 1
}

Write-Host "🧪 Linting..."
pnpm lint
if ($LASTEXITCODE -ne 0) {
  Write-Error "❌ Lint failed."
  exit 1
}

Write-Host "🎨 Formatting check..."
pnpm prettier --check .
if ($LASTEXITCODE -ne 0) {
  Write-Error "❌ Prettier check failed."
  exit 1
}

Write-Host "✅ All dev checks passed!"
