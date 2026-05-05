import type { PluginManifest, Permission } from "./types.js"

export class PluginSandbox {
  private manifests: Map<string, PluginManifest> = new Map()
  private contexts: Map<string, SandboxContext> = new Map()

  async load(pluginId: string, manifest: PluginManifest): Promise<SandboxContext> {
    const ctx: SandboxContext = {
      id: pluginId,
      manifest,
      permissions: new Set(manifest.permissions),
      data: new Map(),
      startTime: Date.now(),
    }
    this.manifests.set(pluginId, manifest)
    this.contexts.set(pluginId, ctx)
    return ctx
  }

  async unload(pluginId: string): Promise<void> {
    this.manifests.delete(pluginId)
    this.contexts.delete(pluginId)
  }

  get(pluginId: string): SandboxContext | undefined {
    return this.contexts.get(pluginId)
  }

  has(pluginId: string): boolean {
    return this.contexts.has(pluginId)
  }

  list(): SandboxContext[] {
    return Array.from(this.contexts.values())
  }
}

export interface SandboxContext {
  id: string
  manifest: PluginManifest
  permissions: Set<Permission>
  data: Map<string, unknown>
  startTime: number
}

export async function validatePlugin(manifest: PluginManifest): Promise<{ valid: boolean; errors: string[] }> {
  const errors: string[] = []

  if (!manifest.id) {
    errors.push("Missing required field: id")
  }
  if (!manifest.name) {
    errors.push("Missing required field: name")
  }
  if (!manifest.version) {
    errors.push("Missing required field: version")
  }
  if (!manifest.compatibility?.opencode) {
    errors.push("Missing required field: compatibility.opencode")
  }

  return {
    valid: errors.length === 0,
    errors,
  }
}

export function createManifest(partial: Partial<PluginManifest>): PluginManifest {
  return {
    id: partial.id ?? "",
    name: partial.name ?? "",
    version: partial.version ?? "1.0.0",
    description: partial.description,
    author: partial.author,
    license: partial.license ?? "MIT",
    compatibility: partial.compatibility ?? { opencode: ">=1.0.0" },
    permissions: partial.permissions ?? [],
    entry: partial.entry ?? "index.js",
    hooks: partial.hooks ?? [],
    dependencies: partial.dependencies ?? {},
    keywords: partial.keywords ?? [],
    homepage: partial.homepage,
    repository: partial.repository,
  }
}
