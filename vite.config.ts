import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import runtimeErrorOverlay from '@replit/vite-plugin-runtime-error-modal';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');

  return {
    root: path.resolve(__dirname, 'client'), // Vite root is the client folder
    plugins: [
      react(),
      runtimeErrorOverlay(),
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'client', 'src'),
        '@shared': path.resolve(__dirname, 'shared'),
        '@assets': path.resolve(__dirname, 'attached_assets'),
      },
    },
    server: {
      watch: {
        usePolling: true, // useful on some OS for file watch reliability
      },
      port: 3000,        // dev server port
      strictPort: true,  // fail if port is taken
      host: true,        // listen on all interfaces (0.0.0.0)
    },
    build: {
      outDir: path.resolve(__dirname, 'server', 'public'), // build output
      emptyOutDir: true,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules')) {
              return id.toString().split('node_modules/')[1].split('/')[0];
            }
          },
        },
      },
    },
  };
});
