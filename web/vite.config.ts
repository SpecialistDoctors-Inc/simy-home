import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';

// Build output goes to ../site/assets so the static-site deploy workflow
// (aws s3 sync site/) picks it up without any CI changes.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/assets/',
  build: {
    outDir: path.resolve(__dirname, '..', 'site', 'assets'),
    emptyOutDir: false, // keep demo-shots/, favicons, etc.
    assetsDir: '.',
    cssCodeSplit: false,
    manifest: false,
    rollupOptions: {
      input: path.resolve(__dirname, 'src', 'main.tsx'),
      output: {
        entryFileNames: 'home-[hash].js',
        chunkFileNames: 'home-[hash].js',
        assetFileNames: (info) => {
          const name = info.names?.[0] ?? '';
          if (name.endsWith('.css')) return 'home-[hash][extname]';
          return '[name]-[hash][extname]';
        },
      },
    },
  },
  server: {
    port: 5173,
  },
});
