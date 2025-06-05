#!/bin/bash
set -e

echo "🧹 Cleaning previous builds..."
tsc --build --clean

echo "📦 Checking TypeScript project references..."
tsc --build tsconfig.json

echo "✅ Type-check passed for all projects."
