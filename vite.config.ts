import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      '/iter': 'http://localhost:5000',
      '/image': 'http://localhost:5000',
      '/tran': 'http://localhost:5000'
    }
  }
})