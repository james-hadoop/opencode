import type { Permission, FileStat } from "../types.js"
import { PERMISSION_LEVELS } from "../types.js"
import { glob } from "glob"

export class FileSystemAPI {
  private rootDir: string
  private permissions: Set<Permission>

  constructor(rootDir: string, permissions: Set<Permission>) {
    this.rootDir = rootDir
    this.permissions = permissions
  }

  private check(perm: Permission): void {
    if (!this.permissions.has(perm)) {
      throw new Error(`Permission denied: ${perm}`)
    }
  }

  private resolve(path: string): string {
    const resolved = path.startsWith("/") ? path : `${this.rootDir}/${path}`
    if (!resolved.startsWith(this.rootDir)) {
      throw new Error(`Access denied: path ${path} is outside root`)
    }
    return resolved
  }

  private get file() {
    return {
      exists: async (path: string) => {
        const fs = await import("fs/promises")
        try {
          await fs.access(path)
          return true
        } catch {
          return false
        }
      },
      read: async (path: string) => {
        const fs = await import("fs/promises")
        return fs.readFile(path, "utf-8")
      },
      write: async (path: string, content: string) => {
        const fs = await import("fs/promises")
        await fs.writeFile(path, content)
      },
      stat: async (path: string) => {
        const fs = await import("fs/promises")
        return fs.stat(path)
      },
    }
  }

  async read(path: string): Promise<string> {
    this.check("fs:read")
    const resolved = this.resolve(path)
    if (!(await this.file.exists(resolved))) {
      throw new Error(`File not found: ${path}`)
    }
    return this.file.read(resolved)
  }

  async readJSON<T>(path: string): Promise<T> {
    const content = await this.read(path)
    return JSON.parse(content)
  }

  async write(path: string, content: string): Promise<void> {
    this.check("fs:write")
    const resolved = this.resolve(path)
    await this.file.write(resolved, content)
  }

  async writeJSON(path: string, data: unknown): Promise<void> {
    await this.write(path, JSON.stringify(data, null, 2))
  }

  async glob(pattern: string): Promise<string[]> {
    this.check("fs:read")
    const matches = await glob(pattern, { cwd: this.rootDir, absolute: true })
    return matches.filter((m) => m.startsWith(this.rootDir))
  }

  async exists(path: string): Promise<boolean> {
    const resolved = this.resolve(path)
    return this.file.exists(resolved)
  }

  async stat(path: string): Promise<FileStat> {
    this.check("fs:read")
    const resolved = this.resolve(path)
    if (!(await this.file.exists(resolved))) {
      throw new Error(`File not found: ${path}`)
    }
    const stats = await this.file.stat(resolved)
    return {
      isFile: stats.isFile(),
      isDirectory: stats.isDirectory(),
      isSymbolicLink: stats.isSymbolicLink(),
      size: stats.size,
      mtime: stats.mtimeMs,
      ctime: stats.ctimeMs,
    }
  }

  get level(): number {
    let maxLevel = 0
    for (const p of this.permissions) {
      const lvl = PERMISSION_LEVELS[p]
      if (lvl !== undefined && lvl > maxLevel) {
        maxLevel = lvl
      }
    }
    return maxLevel
  }
}
