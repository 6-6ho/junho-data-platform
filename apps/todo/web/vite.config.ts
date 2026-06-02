import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSingleFile } from 'vite-plugin-singlefile'

// 단일 index.html 로 번들 (JS·CSS 인라인) → FastMCP 가 / 에서 통째 서빙.
// 폰트만 Pretendard CDN (index.html 의 <link>).
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 4000,
  },
})
