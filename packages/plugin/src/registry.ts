import type { PluginManifest, PluginMetadata, Permission } from "./types.js"
import { MANIFEST_FILENAME, PLUGIN_DIR } from "./types.js"
import { PluginSandbox, validatePlugin } from "./sandbox.js"
import { SecurityManager } from "./security.js"
import * as fs from "fs/promises"
import * as path from "path"

export type PluginState = "pending" | "loading" | "loaded" | "active" | "disabled" | "error"

export interface RegisteredPlugin {
  id: string
  manifest: PluginManifest
  metadata: PluginMetadata
  state: PluginState
  error?: string
  loadTime?: number
}

export class PluginRegistry {
  private sandbox: PluginSandbox
  private security: SecurityManager
  private plugins: Map<string, RegisteredPlugin> = new Map()
  private pluginDir: string

  constructor(pluginDir: string = PLUGIN_DIR) {
    this.pluginDir = pluginDir
    this.sandbox = new PluginSandbox()
    this.security = new SecurityManager()
  }

  async install(source: string): Promise<string> {
    const id = this.generateId()

    const manifest = await this.loadManifest(source)
    const validation = await validatePlugin(manifest)
    if (!validation.valid) {
      throw new Error(`Invalid plugin manifest: ${validation.errors.join(", ")}`)
    }

    const plugin: RegisteredPlugin = {
      id,
      manifest,
      metadata: {
        manifest,
        installedAt: Date.now(),
        enabled: false,
        source: source.startsWith("npm:") ? "npm" : "local",
        path: source,
      },
      state: "pending",
    }

    this.plugins.set(id, plugin)
    this.security.grant(id, manifest.permissions)

    return id
  }

  async enable(pluginId: string): Promise<void> {
    const plugin = this.plugins.get(pluginId)
    if (!plugin) {
      throw new Error(`Plugin not found: ${pluginId}`)
    }

    plugin.state = "loading"
    await this.sandbox.load(pluginId, plugin.manifest)
    plugin.state = "active"
    plugin.metadata.enabled = true
  }

  async disable(pluginId: string): Promise<void> {
    const plugin = this.plugins.get(pluginId)
    if (!plugin) {
      throw new Error(`Plugin not found: ${pluginId}`)
    }

    await this.sandbox.unload(pluginId)
    plugin.state = "disabled"
    plugin.metadata.enabled = false
  }

  async uninstall(pluginId: string): Promise<void> {
    const plugin = this.plugins.get(pluginId)
    if (!plugin) {
      throw new Error(`Plugin not found: ${pluginId}`)
    }

    if (plugin.state === "active") {
      await this.disable(pluginId)
    }

    this.plugins.delete(pluginId)
    this.security.revoke(pluginId)
  }

  get(pluginId: string): RegisteredPlugin | undefined {
    return this.plugins.get(pluginId)
  }

  list(): RegisteredPlugin[] {
    return Array.from(this.plugins.values())
  }

  listEnabled(): RegisteredPlugin[] {
    return this.list().filter((p) => p.metadata.enabled)
  }

  getPermissions(pluginId: string): Permission[] {
    return this.security.getPermissions(pluginId)
  }

  private async loadManifest(source: string): Promise<PluginManifest> {
    if (source.startsWith("npm:")) {
      return this.loadNpmManifest(source.slice(4))
    }
    return this.loadLocalManifest(source)
  }

  private async loadLocalManifest(source: string): Promise<PluginManifest> {
    const manifestPath = path.join(source, MANIFEST_FILENAME)
    const content = await fs.readFile(manifestPath, "utf-8")
    return JSON.parse(content)
  }

  private async loadNpmManifest(packageName: string): Promise<PluginManifest> {
    throw new Error("NPM plugin installation not yet implemented")
  }

  private generateId(): string {
    return `plugin_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`
  }
}

export const registry = new PluginRegistry()
