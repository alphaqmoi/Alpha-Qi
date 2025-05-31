Write-Host "🔧 Installing Husky via PNPM..."
pnpm dlx husky install

$hooks = @{
  "pre-commit" = ".husky/pre-commit"
  "pre-push"   = ".husky/pre-push"
}

foreach ($hook in $hooks.Keys) {
  $path = $hooks[$hook]
  if (-Not (Test-Path $path)) {
    Write-Host "📎 Adding $hook hook..."
    pnpm dlx husky add $path "echo '$hook not yet configured'"
  }
}

if (-Not (Test-Path ".husky/_/husky.sh")) {
  Write-Warning "⚠️ .husky/_/husky.sh missing. Husky may not work properly."
}

Write-Host "✅ Husky setup completed!"
