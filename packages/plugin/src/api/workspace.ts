import type { Permission, PromptTemplate, CodeSnippet, SnippetFilters } from "../types.js"

export class WorkspaceAPI {
  private permissions: Set<Permission>
  private directory: string
  private getConfigFn?: <T>(key: string) => Promise<T | undefined>
  private setConfigFn?: <T>(key: string, value: T) => Promise<void>
  private listPromptsFn?: (teamId: string) => Promise<PromptTemplate[]>
  private addPromptFn?: (prompt: PromptTemplate) => Promise<string>
  private listSnippetsFn?: (teamId: string, filters?: SnippetFilters) => Promise<CodeSnippet[]>
  private addSnippetFn?: (snippet: CodeSnippet) => Promise<string>

  constructor(directory: string, permissions: Set<Permission>) {
    this.directory = directory
    this.permissions = permissions
  }

  private check(perm: Permission): void {
    if (!this.permissions.has(perm)) {
      throw new Error(`Permission denied: ${perm}`)
    }
  }

  setConfigFns(
    get: <T>(key: string) => Promise<T | undefined>,
    set: <T>(key: string, value: T) => Promise<void>,
  ): void {
    this.getConfigFn = get
    this.setConfigFn = set
  }

  setPromptFns(
    list: (teamId: string) => Promise<PromptTemplate[]>,
    add: (prompt: PromptTemplate) => Promise<string>,
  ): void {
    this.listPromptsFn = list
    this.addPromptFn = add
  }

  setSnippetFns(
    list: (teamId: string, filters?: SnippetFilters) => Promise<CodeSnippet[]>,
    add: (snippet: CodeSnippet) => Promise<string>,
  ): void {
    this.listSnippetsFn = list
    this.addSnippetFn = add
  }

  async getConfig<T>(key: string): Promise<T | undefined> {
    this.check("workspace:config")
    if (!this.getConfigFn) {
      throw new Error("Config not available")
    }
    return this.getConfigFn(key)
  }

  async setConfig<T>(key: string, value: T): Promise<void> {
    this.check("workspace:config")
    if (!this.setConfigFn) {
      throw new Error("Config not available")
    }
    return this.setConfigFn(key, value)
  }

  async getSharedPrompt(id: string): Promise<PromptTemplate | undefined> {
    this.check("workspace:prompt")
    if (!this.listPromptsFn) {
      throw new Error("Shared prompts not available")
    }
    const prompts = await this.listPromptsFn("")
    return prompts.find((p) => p.id === id)
  }

  async addSharedPrompt(prompt: PromptTemplate): Promise<string> {
    this.check("workspace:prompt")
    if (!this.addPromptFn) {
      throw new Error("Shared prompts not available")
    }
    return this.addPromptFn(prompt)
  }

  async getCodeSnippet(id: string): Promise<CodeSnippet | undefined> {
    this.check("workspace:snippet")
    if (!this.listSnippetsFn) {
      throw new Error("Code snippets not available")
    }
    const snippets = await this.listSnippetsFn("")
    return snippets.find((s) => s.id === id)
  }

  async addCodeSnippet(snippet: CodeSnippet): Promise<string> {
    this.check("workspace:snippet")
    if (!this.addSnippetFn) {
      throw new Error("Code snippets not available")
    }
    return this.addSnippetFn(snippet)
  }
}
