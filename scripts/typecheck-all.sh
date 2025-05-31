#!/bin/bash
set -e

echo "📦 Checking TypeScript project references..."

# Use tsc with --build mode from root
tsc --build tsconfig.json

echo "✅ Type-check passed for all projects."
