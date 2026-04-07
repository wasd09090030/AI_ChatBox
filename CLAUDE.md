# CLAUDE.md

本文件是本仓库面向 Claude Code 的详细工作说。
当本文件与 `AGENTS.md` 存在冲突时，以本文件为准。

## 文档定位

- `AGENTS.md`：轻量协作规范，适合快速查看。
- `CLAUDE.md`：更完整的仓库事实与架构约定，适合实施前核对。
- `PROJECT_STRUCTURE.md`：更全面的项目结构说明，适合深入理解代码组织。

## 开发命令

### 前端（`frontend/`）

- 安装依赖：`npm install`
- 开发调试：`npm run dev`
- 生产构建：`npm run build`
- 构建预览：`npm run preview`
- 代码检查：`npm run lint`
- 自动修复：`npm run lint:fix`
- 代码格式化：`npm run format`
- 格式校验：`npm run format:check`

### 后端（`story_rag_service/`）

- 安装依赖：`pip install -r requirements.txt`
- 本地启动（热重载）：`uvicorn main:app --reload`
- 备用启动：`python main.py`
- 下载模型资产（按需）：`python download_model.py`
- 迁移数据库：`alembic upgrade head`

## 测试现状

- 当前仓库没有稳定的前后端统一自动化测试套件。
- 不要默认存在 `vitest` 或 `pytest` 目标。
- 搜索测试时忽略第三方目录：
  - `frontend/node_modules/`
  - `story_rag_service/myenv/`

## 仓库结构

- `frontend/`：Vue 3 + TypeScript + Vite 应用。
- `story_rag_service/`：FastAPI 后端（故事生成、lorebook、roleplay、分析等）。
- `AGENTS.md`：仓库简版指南（可能滞后，需与代码现状交叉验证）。
- `PROJECT_STRUCTURE.md`：更全面的项目结构说明，适合深入理解代码组织。

## 前端架构要点

### 应用壳层

- 入口：`frontend/src/main.ts`（挂载 Vue/Pinia/Router/TanStack Query）。
- 路由：`frontend/src/router/index.ts`。
- 主要业务页面：`/story`；后台配置页在 `/dashboard/*`。

### 状态与数据流

- 全局状态主要在 `frontend/src/stores/`。
- `config.ts`：模型/提供商、API Key 状态、主题、provider 级 base URL 配置。
- `storySession.ts`：故事分支、摘要快照、会话级持久状态。
- 远端数据通常用 TanStack Query，本地长生命周期状态用 Pinia。

### API 边界

- HTTP 访问集中在 `frontend/src/domains/**/api` 与 `frontend/src/services/`。
- 故事主 API 客户端：`frontend/src/domains/story/api/storyGenerationApi.ts`。
- 响应校验：`frontend/src/services/schemas.ts`（Zod）。
- 改动后端响应字段时，必须同步更新 TS 类型与 Zod schema。

### 故事 UI

- 主要编排页：`frontend/src/views/StoryView.vue`。
- 子组件分布于 `frontend/src/components/story/`，包含侧栏、对话、控制面板、记忆区、分支树等。
- SSE 流式输出为主：增量追加，终止事件时完成落段。

## 后端架构要点

### FastAPI 入口与服务装配

- 入口：`story_rag_service/main.py`。
- 启动阶段会初始化数据库、用户管理、服务容器。
- 容器装配：`story_rag_service/api/service_context.py`。

### API 组织

- v2 API 汇总：`story_rag_service/api/v2/__init__.py`。
- 新增后端能力优先在 `api/v2/` 下扩展对应 router。

### 故事生成链路

- 非流式主入口：`story_rag_service/api/v2/story/generation_routes.py`。
- 非流式执行：`run_story_graph(...)`（图编排）。
- 流式执行：`ServiceContainer.story_generator.generate_story_stream(...)`（SSE）。
- choices 模式会在路由层做 `[A]/[B]/[C]` 选项解析与最终载荷重写。

### 图编排

- `story_rag_service/graph/story_v2/story_graph.py` 为兼容导出层。
- 实际实现位于：
  - `story_rag_service/graph/story_v2/runtime.py`
  - `story_rag_service/graph/story_v2/nodes.py`

### 生成服务内部

- `story_rag_service/services/story_generator.py` 是编排层。
- 细分能力在 `services/story_generation/`：
  - `llm_factory`
  - `prompt_builder`
  - `context_helpers`
  - `summary_helpers`
- 生成流程融合了世界配置、lorebook 检索、历史检索、角色配置、摘要记忆、provider 客户端等。

### 配置与持久化

- 全局配置：`story_rag_service/config.py`（`pydantic-settings`）。
- 关键配置类别：
  - provider API Key / 默认模型
  - provider base URL
  - Chroma 路径
  - SQLite 路径
  - 检索参数（`top_k_results`、`similarity_threshold`、reranker 开关等）
  - 摘要记忆开关与更新间隔
  - LangGraph checkpoint 后端与路径
- 运行时持久化以 SQLite 为中心；JSON 存储主要用于迁移兼容。

## 变更实践

### 故事能力变更必须走“契约联动”

1. 前端：`storyGenerationApi.ts` / `schemas.ts`
2. 后端：`api/v2/story/*` route/schema
3. 编排层：`graph/story_v2/*` 或 `services/story_generator.py`

### SSE 载荷变更检查点

- 前端 SSE 解析器：`frontend/src/domains/story/api/storyGenerationApi.ts`
- 后端 SSE 封装：`story_rag_service/api/v2/story/generation_routes.py`

### Provider/Model 配置变更检查点

- 前端：`frontend/src/stores/config.ts`
- 后端：`story_rag_service/config.py` 与 `/api/v2/providers*` 路由

### 检索范围建议

- 阅读代码时尽量避开大体量第三方目录，降低噪音：
  - `frontend/node_modules/`
  - `story_rag_service/myenv/`
