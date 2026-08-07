import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8050'

  return {
    plugins: [react()],
    test: {
      environment: 'jsdom',
      setupFiles: './src/test/setupTests.js',
      include: ['src/**/*.test.{js,jsx}', 'tests/**/*.test.{js,jsx}'],
      css: true,
    },
    server: {
      port: 5173,
      proxy: {
        '/auth': apiProxyTarget,
        '/produto': apiProxyTarget,
        '/frete': apiProxyTarget,
        '/modalidade': apiProxyTarget,
        '/vendedor': apiProxyTarget,
        '/usuario': apiProxyTarget,
      },
      allowedHosts: [
        'aspire-banner-neutron.ngrok-free.dev'
      ],
    },
  }
})
