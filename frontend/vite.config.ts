import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const appUrl = new URL(env.VITE_APP_URL || 'http://dukamedev.local:4173')
  const port = appUrl.port
    ? Number(appUrl.port)
    : appUrl.protocol === 'https:'
      ? 443
      : 80

  return {
    plugins: [vue()],
    server: {
      host: appUrl.hostname,
      port,
      strictPort: true,
      proxy: {
        '/api/v1': {
          target: env.DEV_API_PROXY_TARGET || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
