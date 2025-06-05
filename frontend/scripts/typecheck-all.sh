#!/bin/bash
echo "🔍 Running typecheck for all packages..."

# Adjust if you're in a different directory
pnpm tsc -b frontend server shared || {
  echo "❌ Typecheck failed."
  exit 1
}

echo "✅ Typecheck passed for all packages."
