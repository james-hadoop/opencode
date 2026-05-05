import type { Permission } from "../types.js"
import { FileSystemAPI } from "./fs.js"
import { AIServiceAPI } from "./ai.js"
import { UIAPI } from "./ui.js"
import { WorkspaceAPI } from "./workspace.js"

export class PluginAPI {
  readonly fs: FileSystemAPI
  readonly ai: AIServiceAPI
  readonly ui: UIAPI
  readonly workspace: WorkspaceAPI

  constructor(directory: string, permissions: Set<Permission>) {
    this.fs = new FileSystemAPI(directory, permissions)
    this.ai = new AIServiceAPI(permissions)
    this.ui = new UIAPI(permissions)
    this.workspace = new WorkspaceAPI(directory, permissions)
  }
}

export { FileSystemAPI } from "./fs.js"
export { AIServiceAPI } from "./ai.js"
export { UIAPI } from "./ui.js"
export { WorkspaceAPI } from "./workspace.js"
