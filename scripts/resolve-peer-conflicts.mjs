#!/usr/bin/env zx

import { $ } from 'zx'
import { readFile, writeFile, copyFile } from 'fs/promises'
import path from 'path'
import process from 'process'
import { diffLines } from 'diff'
import chalk from 'chalk'

// Step 1: Define paths
const pkgPath = path.resolve(process.cwd(), 'package.json')
const backupPath = path.resolve(process.cwd(), 'package.json.bak')

// Step 2: Backup original package.json
await copyFile(pkgPath, backupPath)
console.log(chalk.blue('📦 Backup created: package.json.bak'))

// Step 3: Load and parse package.json
const pkgRaw = await readFile(pkgPath, 'utf-8')
const pkg = JSON.parse(pkgRaw)

// Step 4: Define patch overrides
const patchOverrides = {
  esbuild: '^0.25.4',
  'vscode-ws-jsonrpc': '^3.4.0',
  '@codingame/monaco-vscode-0c06bfba-d24d-5c4d-90cd-b40cefb7f811-common': '17.1.1',
  '@codingame/monaco-vscode-model-service-override': '17.1.1'
}

// Step 5: Merge into overrides/resolutions
const mergeOverrides = (target = {}) => ({
  ...target,
  ...patchOverrides
})

pkg.overrides = mergeOverrides(pkg.overrides)
pkg.pnpm = pkg.pnpm || {}
pkg.pnpm.overrides = mergeOverrides(pkg.pnpm.overrides)
pkg.resolutions = mergeOverrides(pkg.resolutions)

console.log(chalk.green('🔧 Applied peer conflict overrides'))

// Step 6: Serialize updated package.json
const updatedPkgRaw = JSON.stringify(pkg, null, 2) + '\n'

// Step 7: Show diff summary
console.log(chalk.yellow('\n📋 Changes summary:\n'))
const diff = diffLines(pkgRaw, updatedPkgRaw)
diff.forEach(part => {
  const color = part.added ? 'green' : part.removed ? 'red' : 'gray'
  process.stdout.write(chalk[color](part.value))
})

// Step 8: Save updated package.json
await writeFile(pkgPath, updatedPkgRaw, 'utf-8')
console.log(chalk.blue('\n✅ package.json updated successfully'))

// Step 9: Run pnpm install to apply changes
console.log(chalk.blue('🔄 Running `pnpm install`...'))
await $`pnpm install`
console.log(chalk.green('✅ Dependencies installed successfully.'))
