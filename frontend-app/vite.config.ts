import path from "node:path"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import { defineConfig } from "vite"
import { viteSingleFile } from "vite-plugin-singlefile"

// base './' + single-file JS/CSS so dist/index.html opens via file:// (Chrome blocks external ES modules on file://).
// Video and frames stay as relative files in dist/video/.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss(), viteSingleFile({ removeViteModuleLoader: true })],
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "./src") } },
})
