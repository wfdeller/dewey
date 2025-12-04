import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
    server: {
        port: 5173,
        host: true,
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
        },
    },
    build: {
        sourcemap: true,
        rollupOptions: {
            output: {
                manualChunks: {
                    antd: ['antd', '@ant-design/icons'],
                    charts: ['@ant-design/charts'],
                    react: ['react', 'react-dom', 'react-router-dom'],
                },
            },
        },
    },
});
