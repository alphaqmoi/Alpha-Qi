// resolve-peer-conflicts.mjs
import { $ } from 'zx'

// Ensure this script runs in your monorepo root
console.log('🔧 Resolving peer dependency issues...\n')

try {
  // 1. Downgrade ESLint to compatible version
  console.log('📦 Downgrading ESLint to 8.56.0...')
  await $`pnpm add -D eslint@8.56.0`

  // 2. Align TailwindCSS with plugins
  console.log('📦 Ensuring compatible tailwindcss version (3.4.3)...')
  await $`pnpm add -D tailwindcss@3.4.3`

  // 3. Clean up dependency tree
  console.log('🧹 Dedupe dependencies...')
  await $`pnpm dedupe`

  // 4. Approve build scripts if you're using electron or tailwind oxide
  const autoApprove = true // Set to false to skip this step
  if (autoApprove) {
    console.log('✅ Approving build scripts...')
    await $`pnpm approve-builds`
  }

  console.log('\n✅ Peer dependency issues resolved.')
} catch (err) {
  console.error('\n❌ Something went wrong:', err)
}
