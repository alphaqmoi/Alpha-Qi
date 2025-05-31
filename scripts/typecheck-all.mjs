// scripts/typecheck-all.mjs
import { execSync } from 'child_process';

const projects = ['shared', 'server', 'frontend'];

console.log('🔍 Running type checks across all projects...\n');

for (const project of projects) {
  console.log(`📦 Checking: ${project}`);
  try {
    execSync(`tsc -b ${project}`, { stdio: 'inherit' });
  } catch (err) {
    console.error(`❌ Type check failed in ${project}`);
    process.exit(1);
  }
}

console.log('\n✅ All projects passed type check.');
