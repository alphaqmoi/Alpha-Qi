import js from '@eslint/js';
import globals from 'globals';
import tseslint from 'typescript-eslint';
import pluginReact from 'eslint-plugin-react';
import pluginPrettier from 'eslint-plugin-prettier';
import { defineConfig } from 'eslint/config';

export default defineConfig([
  {
    files: ['**/*.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    plugins: { js },
    extends: ['js/recommended'],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
      parserOptions: {
        ecmaVersion: 2024,
        sourceType: 'module',
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
  },
  // TypeScript rules
  tseslint.configs.recommended,

  // React rules with version config
  {
    ...pluginReact.configs.flat.recommended,
    settings: {
      react: {
        version: 'detect', // 👈 Automatically detect installed React version
      },
    },
  },

  // Prettier rules
  {
    files: ['**/*.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    plugins: { prettier: pluginPrettier },
    rules: {
      'prettier/prettier': 'warn',
    },
    extends: ['prettier'],
  },
]);
