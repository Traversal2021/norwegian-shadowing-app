import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // GitHub Pages deploys to /norwegian-shadowing-app/ when hosted from this repo.
  base: process.env.VITE_BASE_PATH ?? '/',
})
