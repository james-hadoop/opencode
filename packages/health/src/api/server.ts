import { createApp } from "./index"
const app = createApp()
Bun.serve({ port: 3002, fetch: app.fetch })
console.log("API running on http://localhost:3002")
