npx husky add .husky/commit-msg '  
#!/bin/sh
. "$(dirname "$0")/_/husky.sh"

echo "🔍 Validating commit message format..."

npx commitlint --edit "$1" || {
  echo "❌ Commit aborted: Commit message validation failed."
  exit 1
}

echo "✅ Commit message validated."
'
