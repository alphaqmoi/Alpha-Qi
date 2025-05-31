#!/usr/bin/env node

import { execSync } from 'child_process';
import { join } from 'path';

const projects = [
  { name: 'shared', tsconfig: 'shared/tsconfig.json' },
  { name: 'server', tsconfig: 'server/tsconfig.json' },
  { name: 'frontend', tsconfig: 'frontend/tsconfig.json' }
];

const run = (cmd, cwd = '.') => {
  console.log(`\n🔧 Running: ${cmd} in ${cwd}`);
  execSync(cmd, { stdio: 'inherit', cwd });
};

try {
  console.log('🚦 Running type check and lint across all projects...\n');

  for (const project of projects) {
    console.log(`📁 Project: ${project.name}`);

    // Type checking
    run(`pnpm tsc --project ${project.tsconfig}`);

    // Lint with auto-fix
    run(`pnpm eslint . --ext .ts,.tsx,.js,.jsx --fix`, project.name);
  }

  // Root-level checks (optional)
  console.log('\n🧪 Running root-level Prettier check...');
  run(`pnpm prettier --check .`);

  console.log('\n✅ All checks passed successfully.');
} catch (e) {
  console.error('\n❌ Check failed. Please fix the issues above.');
  process.exit(1);
}
