#!/usr/bin/env bash

echo "🚀 Running full DevQmoi workspace checks..."

echo "🔧 Type-checking all TS projects..."
pnpm tsc -b || { echo "❌ Type-check failed."; exit 1; }

echo "🧪 Linting..."
pnpm lint || { echo "❌ Lint failed."; exit 1; }

echo "🎨 Formatting check..."
pnpm prettier --check . || { echo "❌ Prettier check failed."; exit 1; }

echo "✅ All dev checks passed!"
