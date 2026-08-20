import { createReadStream, existsSync, statSync } from 'node:fs'
import { createServer } from 'node:http'
import { extname, join, normalize } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('./dist/', import.meta.url))
const port = Number(process.env.PORT || 3000)
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon', '.json': 'application/json' }
createServer((request, response) => {
  const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname)
  const candidate = normalize(join(root, pathname))
  const safe = candidate.startsWith(root) ? candidate : join(root, 'index.html')
  const file = existsSync(safe) && statSync(safe).isFile() ? safe : join(root, 'index.html')
  response.setHeader('Content-Type', types[extname(file)] || 'application/octet-stream')
  response.setHeader('X-Content-Type-Options', 'nosniff')
  createReadStream(file).pipe(response)
}).listen(port, '0.0.0.0', () => console.log(`HomeWiseEdu frontend listening on ${port}`))
