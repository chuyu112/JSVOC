import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          const normalizedId = id.replaceAll('\\', '/')

          if (!normalizedId.includes('/node_modules/')) {
            return undefined
          }
          if (normalizedId.includes('/element-plus/')) {
            return 'ui-vendor'
          }
          if (
            normalizedId.includes('/vue/') ||
            normalizedId.includes('/vue-router/') ||
            normalizedId.includes('/pinia/')
          ) {
            return 'vue-vendor'
          }
          if (normalizedId.includes('/axios/')) {
            return 'data-vendor'
          }
          return 'vendor'
        },
      },
    },
  },
})
