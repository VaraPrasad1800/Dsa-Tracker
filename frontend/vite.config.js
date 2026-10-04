import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backendTarget = (env.VITE_API_URL ? env.VITE_API_URL.replace(/\/api\/?$/, '') : 'http://127.0.0.1:8001')
    .replace(/^https:\/\/(localhost|127\.0\.0\.1)/, 'http://$1');

  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
});

