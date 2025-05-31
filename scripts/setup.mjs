#!/usr/bin/env node

import { execSync, existsSync, mkdirSync, writeFileSync, readdirSync, statSync } from 'fs';
import { join } from 'path';

const run = (cmd) => {
  console.log(`$ ${cmd}`);
  execSync(cmd, { stdio: 'inherit' });
};

const huskyHook = (relativePath, content) => {
  const fullPath = join('.husky', relativePath);
  writeFileSync(fullPath, content.replace(/\r?\n/g, '\n'), { mode: 0o755 });
  console.log(`✅ Hook created: ${fullPath}`);
};

const runInitialChecks = () => {
  const checks = [
    ['🔍 Type check', 'pnpm tsc -b'],
    ['🔎 Lint', 'pnpm eslint . --ext .ts,.tsx,.js,.jsx'],
    ['🎨 Prettier', 'pnpm prettier --check .'],
    ['🧪 Vitest', 'pnpm vitest run'],
    ['🎨 Stylelint', 'pnpm stylelint "**/*.{css,scss}"']
  ];

  for (const [label, cmd] of checks) {
    console.log(`\n${label}: ${cmd}`);
    try {
      execSync(cmd, { stdio: 'inherit' });
    } catch (e) {
      console.error(`❌ Failed: ${label}`);
      process.exit(1);
    }
  }

  console.log('\n✅ All initial checks passed.\n');
};

const getProjectDirs = () => {
  const exclude = ['.git', 'node_modules', '.husky', 'dist', 'build', 'scripts'];
  return readdirSync('.').filter(
    (name) => !exclude.includes(name) && statSync(name).isDirectory()
  );
};

const setupHusky = () => {
  if (!existsSync('.husky')) {
    run('pnpm dlx husky-init && pnpm install');
  }

  huskyHook('pre-commit', `#!/bin/sh
. "$(dirname "$0")/_/husky.sh"
echo "🔍 Pre-commit checks..."

bash -c '
  STAGED=$(git diff --cached --name-only --diff-filter=ACMRT | grep -E "\\.(ts|tsx|js|jsx|json|css|scss|md)$")
  if [ -z "$STAGED" ]; then echo "✅ No matching files."; exit 0; fi
  echo "🧹 Running lint-staged..."; npx lint-staged
' || {
  if [ "$OS" = "Windows_NT" ]; then
    pwsh -Command '
      $files = git diff --cached --name-only --diff-filter=ACMRT | Where-Object { $_ -match "\\.(ts|tsx|js|jsx|json|css|scss|md)$" }
      if (-not $files) { Write-Host "✅ No matching files."; exit 0 }
      npx lint-staged
    ' || { echo "❌ Commit failed."; exit 1; }
  else
    echo "❌ Bash failed and no fallback available."; exit 1;
  fi
}
echo "✅ Pre-commit passed."`);

  huskyHook('pre-push', `#!/bin/sh
. "$(dirname "$0")/_/husky.sh"
echo "🚀 Pre-push checks..."

bash -c '
  pnpm run check && pnpm vitest run && pnpm stylelint "**/*.{css,scss}"
' || {
  if [ "$OS" = "Windows_NT" ]; then
    pwsh -Command "
      pnpm run check; if ($?) {
        pnpm vitest run
        pnpm stylelint \\"**/*.{css,scss}\\"
      } else {
        exit 1
      }
    " || { echo "❌ Push failed."; exit 1; }
  else
    echo "❌ Bash failed and no fallback."; exit 1;
  fi
}
echo "✅ Pre-push passed."`);
};

const setupProjectHooks = () => {
  const dirs = getProjectDirs();
  for (const dir of dirs) {
    const hookDir = join(dir, '.husky');
    if (!existsSync(hookDir)) mkdirSync(hookDir, { recursive: true });

    const huskyShPath = join(hookDir, '_/husky.sh');
    if (!existsSync(huskyShPath)) {
      writeFileSync(huskyShPath, `. "$(dirname "$0")/../node_modules/husky/husky.sh"\n`, { mode: 0o755 });
    }

    const precommitPath = join(hookDir, 'pre-commit');
    const prepPushPath = join(hookDir, 'pre-push');

    if (!existsSync(precommitPath)) {
      writeFileSync(precommitPath, `#!/bin/sh
. "$(dirname "$0")/_/husky.sh"

echo "🔍 ${dir} pre-commit hook..."

pnpm prettier --check . || exit 1
pnpm eslint --ext .ts,.tsx . || exit 1
pnpm stylelint "**/*.{css,scss}" || exit 1
echo "✅ ${dir} pre-commit passed."
`, { mode: 0o755 });
    }

    if (!existsSync(prepPushPath)) {
      writeFileSync(prepPushPath, `#!/bin/sh
. "$(dirname "$0")/_/husky.sh"

echo "🚀 ${dir} pre-push hook..."

cd ${dir}
pnpm tsc --noEmit || exit 1
pnpm vitest run || exit 1
pnpm eslint --ext .ts,.tsx . || exit 1
echo "✅ ${dir} pre-push passed."
`, { mode: 0o755 });
    }
  }
};

runInitialChecks();
setupHusky();
setupProjectHooks();

console.log('\n🎉 Husky + CI hooks fully set up for all projects.\n');
