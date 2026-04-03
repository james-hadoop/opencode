import type { Permission, CompleteOptions, EmbedOptions } from "../types.js"

export class AIServiceAPI {
  private permissions: Set<Permission>
  private completeFn?: (prompt: string, opts?: CompleteOptions) => Promise<string>
  private embedFn?: (text: string, opts?: EmbedOptions) => Promise<number[]>

  constructor(permissions: Set<Permission>) {
    this.permissions = permissions
  }

  private check(perm: Permission): void {
    if (!this.permissions.has(perm)) {
      throw new Error(`Permission denied: ${perm}`)
    }
  }

  setCompleteFn(fn: (prompt: string, opts?: CompleteOptions) => Promise<string>): void {
    this.completeFn = fn
  }

  setEmbedFn(fn: (text: string, opts?: EmbedOptions) => Promise<number[]>): void {
    this.embedFn = fn
  }

  async complete(prompt: string, options?: CompleteOptions): Promise<string> {
    this.check("ai:complete")
    if (!this.completeFn) {
      throw new Error("AI complete function not configured")
    }
    return this.completeFn(prompt, options)
  }

  async embed(text: string, options?: EmbedOptions): Promise<number[]> {
    this.check("ai:embed")
    if (!this.embedFn) {
      throw new Error("AI embed function not configured")
    }
    return this.embedFn(text, options)
  }

  async stream(prompt: string, onChunk: (chunk: string) => void, options?: CompleteOptions): Promise<void> {
    this.check("ai:stream")
    const result = await this.complete(prompt, options)
    onChunk(result)
  }
}
