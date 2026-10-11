import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// The stylesheet is small (about 10 kB compressed), and as a separate file it
// held up the first paint for a whole extra round trip on a slow phone. Put
// it in the page itself. The file is still emitted: lazy chunks may name it.
function inlineEntryCss() {
  return {
    name: 'inline-entry-css',
    apply: 'build',
    enforce: 'post',
    transformIndexHtml: {
      order: 'post',
      handler(html, ctx) {
        return html.replace(
          /<link rel="stylesheet"[^>]*href="\/(assets\/[^"]+\.css)"[^>]*>/g,
          (tag, file) => {
            const css = ctx.bundle?.[file]?.source
            return css ? `<style data-href="/${file}">${css}</style>` : tag
          },
        )
      },
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), inlineEntryCss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rolldownOptions: {
      output: {
        // Every icon is a few hundred bytes. Left alone, each one shared by two
        // pages becomes its own file, and the landing page waited on a dozen
        // tiny requests before it could start. One file for all of them.
        advancedChunks: {
          groups: [
            { name: 'icons', test: /node_modules\/@tabler\// },
            { name: 'vendor', test: /node_modules\/(react|react-dom|scheduler|react-router|react-router-dom|zustand)\// },
            { name: 'common', test: /\/src\//, minShareCount: 3 },
          ],
        },
      },
    },
  },
  server: {
    port: 5173,
    // pages/admin/AdminHelp shows docs/OWNER_GUIDE.md, one level above this folder.
    fs: { allow: ['..'] },
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/static/uploads': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
