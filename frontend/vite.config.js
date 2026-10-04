import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const rawTarget = env.VITE_API_URL || env.VITE_BACKEND_URL || `http://127.0.0.1:${env.VITE_BACKEND_PORT || '8000'}`;
  const backendTarget = rawTarget
    .replace(/^https:\/\/(localhost|127\.0\.0\.1)/, 'http://$1')
    .replace(/\/api\/?$/, '');

  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true,
      https: false,
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

