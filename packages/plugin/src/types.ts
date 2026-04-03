import type { z } from "zod"

export type Permission =
  | "fs:read"
  | "fs:write"
  | "fs:execute"
  | "fs:delete"
  | "network:request"
  | "network:connect"
  | "ai:complete"
  | "ai:embed"
  | "ai:stream"
  | "ui:render"
  | "ui:notification"
  | "ui:dialog"
  | "workspace:config"
  | "workspace:prompt"
  | "workspace:snippet"
  | "system:env"
  | "system:shell"
  | "system:plugin"

export type PermissionLevel = 0 | 1 | 2 | 3 | 4

export const PERMISSION_LEVELS: Record<Permission, PermissionLevel> = {
  "fs:read": 1,
  "fs:write": 2,
  "fs:execute": 2,
  "fs:delete": 3,
  "network:request": 3,
  "network:connect": 3,
  "ai:complete": 1,
  "ai:embed": 1,
  "ai:stream": 1,
  "ui:render": 0,
  "ui:notification": 0,
  "ui:dialog": 0,
  "workspace:config": 2,
  "workspace:prompt": 1,
  "workspace:snippet": 1,
  "system:env": 3,
  "system:shell": 4,
  "system:plugin": 4,
}

export interface PluginAuthor {
  name: string
  email?: string
  url?: string
}

export interface PluginCompatibility {
  opencode: string
}

export interface PluginManifest {
  id: string
  name: string
  version: string
  description?: string
  author?: PluginAuthor
  license?: string
  compatibility: PluginCompatibility
  permissions: Permission[]
  entry?: string
  hooks?: string[]
  dependencies?: Record<string, string>
  keywords?: string[]
  homepage?: string
  repository?: string
}

export interface PluginMetadata {
  manifest: PluginManifest
  installedAt: number
  enabled: boolean
  source: "local" | "npm" | "marketplace"
  path?: string
  checksum?: string
  signature?: string
}

export interface PluginCode {
  manifest: PluginManifest
  code: string | Uint8Array
  dependencies?: Record<string, string>
}

export interface FileStat {
  isFile: boolean
  isDirectory: boolean
  isSymbolicLink: boolean
  size: number
  mtime: number
  ctime: number
}

export interface CompleteOptions {
  model?: string
  temperature?: number
  maxTokens?: number
  stop?: string[]
}

export interface EmbedOptions {
  model?: string
}

export interface DialogOptions {
  title?: string
  message: string
  type?: "info" | "warning" | "error" | "question"
  buttons?: string[]
  defaultButton?: number
}

export interface DialogResult {
  button: number
  response?: string
}

export interface PromptTemplate {
  id: string
  name: string
  content: string
  variables: string[]
  description?: string
  tags?: string[]
}

export interface CodeSnippet {
  id: string
  name: string
  description?: string
  language: string
  code: string
  tags?: string[]
}

export interface SnippetFilters {
  language?: string
  tags?: string[]
  search?: string
}

export type PluginEvent =
  | { type: "install"; pluginId: string }
  | { type: "uninstall"; pluginId: string }
  | { type: "enable"; pluginId: string }
  | { type: "disable"; pluginId: string }
  | { type: "error"; pluginId: string; error: Error }

export type HookName =
  | "tool.definition"
  | "tool.execute.before"
  | "tool.execute.after"
  | "chat.message"
  | "chat.params"
  | "chat.headers"
  | "permission.ask"
  | "command.execute.before"
  | "shell.env"
  | "experimental.chat.messages.transform"
  | "experimental.chat.system.transform"
  | "experimental.session.compacting"
  | "experimental.text.complete"

export interface PluginContext {
  directory: string
  worktree: string
  permissions: Set<Permission>
  sandbox: boolean
}

export const MANIFEST_FILENAME = "opencode-plugin.json"
export const PLUGIN_DIR = ".opencode/plugins"
