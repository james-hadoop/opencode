---
status: draft
created: 2026-03-24
ceo-review-mode: SCOPE EXPANSION
selected-proposals:
  - proposal-1: 插件系统架构
  - proposal-3: 团队协作功能
---

# OpenCode Plugin & Team Collaboration Specification

## 概述

本 SPEC 定义了两个核心功能的实现方案：

| 功能         | 描述                          | 优先级 |
| ------------ | ----------------------------- | ------ |
| 插件系统架构 | 开放的插件 API 和生态系统基础 | P0     |
| 团队协作功能 | 共享配置、prompt 库、代码片段 | P1     |

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                     OpenCode Platform                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐            │
│  │   CLI/TUI   │   │   Desktop   │   │  Web/API    │            │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘            │
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                           │                                      │
│                    ┌──────▼──────┐                               │
│                    │    Core    │                               │
│                    └──────┬──────┘                               │
│                           │                                      │
│    ┌──────────────────────┼──────────────────────┐             │
│    │                      │                      │             │
│ ┌──▼─────┐         ┌──────▼──────┐        ┌──────▼─────┐      │
│ │Plugin  │         │    Team     │        │   Model    │      │
│ │Manager │         │   Service   │        │   Router   │      │
│ └────────┘         └─────────────┘        └────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 1: 插件系统架构

### 1.1 核心目标

- 提供稳定的 Plugin API (v1)
- 支持第三方插件安全运行
- 简单的发布和分发机制

### 1.2 目录结构

```
packages/plugin/
├── src/
│   ├── index.ts              # 现有 - Hooks 定义
│   ├── tool.ts                # 现有 - ToolDefinition
│   ├── shell.ts               # 现有 - BunShell
│   ├── registry.ts            # NEW - 插件注册表
│   ├── sandbox.ts             # NEW - 沙箱执行环境
│   ├── security.ts            # NEW - 权限和安全
│   ├── manifest.ts            # NEW - manifest.json 解析
│   └── lifecycle.ts           # NEW - 插件生命周期
├── api/
│   └── v1/                    # NEW - 公开 API
│       ├── index.ts
│       ├── fs.ts               # 文件系统 API
│       ├── ai.ts               # AI 服务 API
│       ├── ui.ts               # UI 交互 API
│       └── workspace.ts        # 工作区 API
├── registry/
│   └── index.ts               # NEW - 插件市场
└── types/
    └── index.ts               # NEW - 类型定义
```

### 1.3 插件 Manifest

```typescript
// packages/plugin/types/index.ts
export interface PluginManifest {
  id: string
  name: string
  version: string
  description?: string
  author?: {
    name: string
    email?: string
    url?: string
  }
  license?: string
  compatibility: {
    opencode: string // e.g., ">=1.0.0"
  }
  permissions: Permission[]
  entry?: string
  hooks?: string[]
  dependencies?: Record<string, string>
}

export type Permission =
  | "fs:read"
  | "fs:write"
  | "fs:execute"
  | "network:request"
  | "ai:complete"
  | "ai:embed"
  | "ui:render"
  | "workspace:config"
  | "workspace:prompt"
```

### 1.4 Plugin API (v1)

```typescript
// packages/plugin/api/v1/index.ts
export class PluginAPI {
  readonly fs: FileSystemAPI
  readonly ai: AIServiceAPI
  readonly ui: UIAPI
  readonly workspace: WorkspaceAPI
  readonly config: ConfigAPI
}

// 文件系统 API - 受限于 permission
export class FileSystemAPI {
  read(path: string): Promise<string>
  readJSON<T>(path: string): Promise<T>
  write(path: string, content: string): Promise<void>
  writeJSON(path: string, data: any): Promise<void>
  glob(pattern: string): Promise<string[]>
  exists(path: string): Promise<boolean>
  stat(path: string): Promise<FileStat>
  // 注意: 无 delete/move 等危险操作，需单独 permission
}

// AI 服务 API
export class AIServiceAPI {
  complete(prompt: string, options?: CompleteOptions): Promise<string>
  embed(text: string): Promise<number[]>
  stream(prompt: string, onChunk: (chunk: string) => void): Promise<void>
}

// UI 交互 API
export class UIAPI {
  showNotification(message: string, type?: "info" | "success" | "error"): void
  showDialog(options: DialogOptions): Promise<DialogResult>
  renderMarkdown(markdown: string): Promise<void>
}

// 工作区 API
export class WorkspaceAPI {
  getConfig<T>(key: string): Promise<T | undefined>
  setConfig<T>(key: string, value: T): Promise<void>
  getSharedPrompt(id: string): Promise<PromptTemplate>
  addSharedPrompt(prompt: PromptTemplate): Promise<string>
  getCodeSnippet(id: string): Promise<CodeSnippet>
  addCodeSnippet(snippet: CodeSnippet): Promise<string>
}
```

### 1.5 沙箱执行

```typescript
// packages/plugin/src/sandbox.ts
import { WasmRuntime } from "@aspect-dev/wasm-runtime"

export class PluginSandbox {
  private runtime: WasmRuntime

  async load(plugin: PluginCode): Promise<SandboxedPlugin> {
    // 1. 验证 manifest
    // 2. 创建 isolated context
    // 3. 加载 WASM 运行时
    // 4. 注入受限制的 API
  }

  async execute(plugin: SandboxedPlugin, method: string, args: any[]): Promise<any> {
    // 在 WASM 沙箱中执行
  }
}
```

### 1.6 权限系统

```
┌─────────────────────────────────────────┐
│         Permission Hierarchy            │
├─────────────────────────────────────────┤
│                                         │
│  Level 0: None                          │
│  ├─ read only API access                │
│  └─ no file/system access               │
│                                         │
│  Level 1: Read                          │
│  ├─ read file system                    │
│  ├─ read config                         │
│  └─ no modifications                    │
│                                         │
│  Level 2: Basic                         │
│  ├─ read + write own files              │
│  ├─ execute safe commands               │
│  └─ no network access                   │
│                                         │
│  Level 3: Full                          │
│  ├─ full file access                    │
│  ├─ network requests                    │
│  └─ shell execution                      │
│                                         │
│  Level 4: Admin                          │
│  ├─ system configuration                │
│  ├─ plugin management                   │
│  └─ sensitive data access               │
│                                         │
└─────────────────────────────────────────┘
```

### 1.7 插件生命周期

```
install ──▶ validate ──▶ download ──▶ verify ──▶ extract ──▶ register ──▶ activate
   │          │           │          │          │            │            │
   ▼          ▼           ▼          ▼          ▼            ▼            ▼
[source]  [manifest]  [package]  [signature] [extract]   [registry]   [ready]
           [perm]     [checksum] [checksum]  [sandbox]   [events]    [running]
```

### 1.8 实现步骤

| Step | Task                                         | Duration |
| ---- | -------------------------------------------- | -------- |
| 1    | 定义 PluginManifest 类型                     | 1 day    |
| 2    | 实现 Plugin API (fs, ai, ui, workspace)      | 2 days   |
| 3    | 实现权限检查系统                             | 1 day    |
| 4    | 实现沙箱执行环境 (WASM)                      | 3 days   |
| 5    | 实现插件注册表和生命周期                     | 2 days   |
| 6    | CLI 命令: plugin install/list/enable/disable | 1 day    |
| 7    | 测试和安全审计                               | 2 days   |

---

## Part 2: 团队协作功能

### 2.1 核心目标

- 团队配置同步
- 共享 Prompt 库
- 代码片段共享

### 2.2 数据模型

```typescript
// src/team/schema.ts
export const teamTable = sqliteTable("team", {
  id: text().primaryKey(),
  name: text().notNull(),
  createdAt: integer().notNull(),
  createdBy: text().notNull(),
})

export const teamMemberTable = sqliteTable("team_member", {
  teamId: text()
    .notNull()
    .references(() => teamTable.id),
  userId: text().notNull(),
  role: text().notNull(), // "admin" | "member"
  joinedAt: integer().notNull(),
})

export const sharedPromptTable = sqliteTable("shared_prompt", {
  id: text().primaryKey(),
  teamId: text()
    .notNull()
    .references(() => teamTable.id),
  name: text().notNull(),
  content: text().notNull(),
  variables: text(), // JSON array of variable names
  createdBy: text().notNull(),
  createdAt: integer().notNull(),
  updatedAt: integer().notNull(),
})

export const codeSnippetTable = sqliteTable("code_snippet", {
  id: text().primaryKey(),
  teamId: text()
    .notNull()
    .references(() => teamTable.id),
  name: text().notNull(),
  description: text(),
  language: text().notNull(),
  code: text().notNull(),
  tags: text(), // JSON array
  createdBy: text().notNull(),
  createdAt: integer().notNull(),
})

export const teamConfigTable = sqliteTable("team_config", {
  teamId: text()
    .notNull()
    .references(() => teamTable.id),
  key: text().notNull(),
  value: text().notNull(), // JSON
  updatedAt: integer().notNull(),
  updatedBy: text().notNull(),
})
```

### 2.3 同步架构

```
┌─────────────────────────────────────────────────────┐
│            Team Sync Architecture                   │
├─────────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │  Client  │    │  Server  │    │   Sync   │   │
│  │  Local   │◄──►│   API    │◄──►│  Engine  │   │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘   │
│       │                │                │          │
│       │         ┌──────▼──────┐         │          │
│       │         │   Database  │         │          │
│       │         │  (Postgres) │         │          │
│       │         └─────────────┘         │          │
│       │                                  │          │
│       │    ┌─────────────────────┐        │          │
│       └───►│  CRDT Conflict      │◄───────┘          │
│            │  Resolution         │                   │
│            └─────────────────────┘                   │
└─────────────────────────────────────────────────────┘
```

### 2.4 Team Service API

```typescript
// src/team/service.ts
export class TeamService {
  // 团队管理
  async createTeam(name: string): Promise<Team>
  async joinTeam(inviteCode: string): Promise<TeamMember>
  async leaveTeam(teamId: string): Promise<void>

  // 配置同步
  async syncConfig(teamId: string): Promise<TeamConfig>
  async pushConfig(teamId: string, key: string, value: any): Promise<void>
  async pullConfig(teamId: string): Promise<Record<string, any>>

  // 共享 Prompt
  async listPrompts(teamId: string): Promise<SharedPrompt[]>
  async createPrompt(teamId: string, prompt: PromptInput): Promise<SharedPrompt>
  async updatePrompt(id: string, prompt: Partial<PromptInput>): Promise<SharedPrompt>
  async deletePrompt(id: string): Promise<void>

  // 代码片段
  async listSnippets(teamId: string, filters?: SnippetFilters): Promise<CodeSnippet[]>
  async createSnippet(teamId: string, snippet: SnippetInput): Promise<CodeSnippet>
  async searchSnippets(teamId: string, query: string): Promise<CodeSnippet[]>
}
```

### 2.5 冲突解决策略

```typescript
// CRDT-based conflict resolution
type ConflictStrategy = "last-write-wins" | "merge" | "manual"

interface TeamConfig {
  strategy: ConflictStrategy
  mergeRules?: {
    // 对于不同类型的配置使用不同策略
    "prompts.*": "last-write-wins"
    "coding-standards": "merge" // 合并 JSON
    "tool-config": "manual" // 需要手动解决
  }
}
```

### 2.6 实现步骤

| Step | Task                            | Duration |
| ---- | ------------------------------- | -------- |
| 1    | 设计并创建 team 数据库表        | 1 day    |
| 2    | 实现 Team Service 核心方法      | 2 days   |
| 3    | 实现配置同步引擎 (CRDT)         | 3 days   |
| 4    | 实现共享 Prompt API             | 1 day    |
| 5    | 实现代码片段 API + 搜索         | 2 days   |
| 6    | 实现邀请和权限系统              | 1 day    |
| 7    | CLI 命令: team create/join/sync | 1 day    |
| 8    | 前端界面 (如果需要)             | 2 days   |

---

## API 兼容性策略

### Versioning

- Plugin API 使用语义化版本
- 每个主版本提供 12 个月的支持
- 废弃 API 提前 6 个月通知

### 迁移路径

```
v1.0 ──▶ v1.1 ──▶ v2.0
  │        │        │
  │        └────┬───┘
  │             │
  │     deprecated + warnings
  │             │
  └─────────────┘
        migration guide
```

---

## 测试策略

### 单元测试

```typescript
// plugin/api/v1/fs.test.ts
describe("FileSystemAPI", () => {
  it("should respect read permission only", async () => {
    const api = new FileSystemAPI({ permissions: ["fs:read"] })
    await api.read("/project/file.txt")
    await expect(api.write("/project/file.txt", "data")).rejects.toThrow()
  })

  it("should sandbox path access", async () => {
    const api = new FileSystemAPI({ rootDir: "/project" })
    await expect(api.read("/etc/passwd")).rejects.toThrow()
  })
})

// team/service.test.ts
describe("TeamService", () => {
  it("should sync config between members", async () => {
    // 创建团队
    // 修改配置
    // 验证同步
  })

  it("should resolve merge conflicts", async () => {
    // 模拟两个客户端同时修改
    // 验证冲突解决
  })
})
```

### 集成测试

- 完整插件安装/执行流程
- 团队创建、加入、同步流程
- 权限边界测试

### 安全测试

- 恶意插件行为测试
- 权限提升尝试测试
- 注入攻击测试

---

## 部署计划

### 特性开关

| Feature  | Key                          | Rollout          |
| -------- | ---------------------------- | ---------------- |
| 插件系统 | `feature.plugins`            | 10% → 50% → 100% |
| 团队协作 | `feature.teams`              | 10% → 50% → 100% |
| 插件市场 | `feature.plugin_marketplace` | 5% → 25% → 100%  |

### 回滚方案

| Scenario     | Rollback                    |
| ------------ | --------------------------- |
| 插件系统崩溃 | 禁用第三方插件，只保留内置  |
| 团队同步故障 | 本地缓存模式 + 告警         |
| 安全漏洞     | 紧急发布禁用受影响插件/功能 |

---

## 时间线

```
Q1 (4-6月)                    Q2 (7-9月)                    Q3 (10-12月)
─────────────────────────────────────────────────────────────────────────
Plugin API v1                 插件市场 Beta                插件 v1.0
Sandbox 沙箱                  团队配置同步                 团队协作 v1.0
权限系统                      共享 Prompt 库               稳定性优化
                             代码片段库
```

---

## 待讨论问题

1. **插件市场托管**: 自建还是使用现有 npm registry?
2. **团队存储**: 本地 SQLite 还是云端 Postgres?
3. **认证方式**: 团队邀请码 vs OAuth?
