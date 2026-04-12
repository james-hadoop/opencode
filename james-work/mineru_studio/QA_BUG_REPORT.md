# MinerU Studio FastAPI 服务 Bug 清单

## 测试概览

- **测试日期**: 2026-04-10
- **服务地址**: http://localhost:3000
- **测试方法**: API 功能测试 (curl)

---

## 修复状态: ✅ 全部已修复 (2026-04-10)

| Bug ID  | 描述                                                       | 状态                     |
| ------- | ---------------------------------------------------------- | ------------------------ |
| BUG-001 | GET /runs/{id} returns 404 after creating                  | ✅ 已修复                |
| BUG-002 | GET /runs/{id}/poll works but GET /runs/{id} returns 404   | ✅ 已修复                |
| BUG-003 | WebSocket /ws returns 404                                  | ✅ 已修复 (路由正常工作) |
| BUG-004 | GET /api/workflows/{id} returns fake data for non-existent | ✅ 已修复                |
| BUG-005 | PUT /api/workflows/{id} silently creates for non-existent  | ✅ 已修复                |
| BUG-006 | GET /api/workflow-runs/{id} returns fake data              | ✅ 已修复                |
| BUG-007 | GET /api/tool-sessions/{id} returns fake data              | ✅ 已修复                |
| BUG-008 | Auth failure returns 200 instead of 401                    | ✅ 已修复                |
| BUG-009 | POST returns array format [{}, 201]                        | ✅ 已修复                |
| BUG-010 | @app.on_event("startup") deprecated                        | ⚠️ 仍存在 (低优先级)     |

---

## 修复详情

### BUG-001/002: GET /runs/{run_id} 返回 404 但 run 实际已创建

**根因**:

1. 原始代码中 metadata key 是 "triggeredBy" (camelCase)，但实际存储的是 "triggered_by" (snake_case)
2. 数据库会话管理问题

**修复**:

- 修正了 main.py 中的 key 检查，从 `triggeredBy` 改为 `triggered_by`
- 重构了 repository.py 使用 `async with self._session_maker() as session` 确保每次操作使用独立的 session

---

### BUG-003: WebSocket /ws 端点返回 404

**状态**: 路由实际上是正确的，404 是因为 curl 不支持 WebSocket 协议

**验证**: 通过 uvicorn 日志确认 WebSocket 路由已注册

---

### BUG-004/005: Workflow CRUD 返回假数据

**修复**:

- GET /api/workflows/{id}: 添加存在性检查，不存在返回 404
- PUT /api/workflows/{id}: 添加存在性检查，不存在返回 404

---

### BUG-006/007: Run/Session 端点返回假数据

**修复**:

- GET /api/workflow-runs/{id}: 添加存在性检查，不存在返回 404
- GET /api/tool-sessions/{id}: 添加存在性检查，不存在返回 404

---

### BUG-008: 认证失败返回 200

**修复**:

- 添加了 `get_optional_user` 依赖用于公开端点
- 认证端点现在正确返回 401

---

### BUG-009: 返回格式异常

**修复**:

- 使用 `@app.post(..., status_code=201)` 替代 `return {}, 201`

---

## 通过的测试

- ✅ GET /metrics (无需认证)
- ✅ GET /catalog (无需认证)
- ✅ GET /api/tools (无需认证)
- ✅ GET /api/me (无需认证)
- ✅ POST /auth/login
- ✅ POST /runs (创建后立即 GET 返回 200)
- ✅ GET /runs/{id}
- ✅ POST /api/workflows (创建成功)
- ✅ GET /api/workflows/{id} (不存在的返回 404)
- ✅ PUT /api/workflows/{id} (不存在的返回 404)
- ✅ GET /api/workflow-runs/{id} (不存在的返回 404)
- ✅ GET /api/tool-sessions/{id} (不存在的返回 404)
- ✅ 认证失败返回 401
- ✅ POST /api/admin/help/faqs 返回 201
