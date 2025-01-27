import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  base: '/jpegtranweb/',
  plugins: [svelte()],
  server: {
    proxy: {
      '/iter': 'http://localhost:5000',
      '/image': 'http://localhost:5000',
      '/tran': 'http://localhost:5000'
    }
  }
})