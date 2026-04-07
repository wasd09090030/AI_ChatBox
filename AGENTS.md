# 仓库协作指南

## 项目结构与模块分层
- `frontend/`：Vue 3 + TypeScript + Vite 前端。
  - 入口：`src/main.ts`
  - 路由：`src/router`
  - 状态：`src/stores`
  - 业务 API：`src/domains/**/api`
  - 通用服务：`src/services`
- `story_rag_service/`：FastAPI 后端。
  - 入口：`main.py`
  - API：`api/v2/`
  - 服务装配：`api/service_context.py`
  - 业务服务：`services/`
  - 图编排：`graph/story_v2/`
- `Nginx.txt`：部署与反向代理说明。
- `CLAUDE.md`：仓库级详细规范；若与本文件冲突，以 `CLAUDE.md` 为准。

## 开发命令

### 前端（`frontend/`）
- 安装依赖：`npm install`
- 启动开发：`npm run dev`
- 构建产物：`npm run build`
- 预览构建：`npm run preview`
- 代码检查：`npm run lint`
- 自动修复：`npm run lint:fix`
- 代码格式化：`npm run format`
- 格式校验：`npm run format:check`

### 后端（`story_rag_service/`）
- 创建虚拟环境（示例）：
  - `python -m venv myenv`
  - `myenv\Scripts\Activate.ps1`
- 安装依赖：`pip install -r requirements.txt`
- 启动 API（热重载）：`uvicorn main:app --reload`
- 备用启动：`python main.py`
- 下载模型资产（按需）：`python download_model.py`
- 执行迁移：`alembic upgrade head`

## 测试与验证说明
- 当前仓库没有稳定的前后端统一自动化测试套件。
- 不要默认存在 `vitest` 或 `pytest` 命令，除非任务明确添加或指定。
- 搜索测试文件时请忽略第三方目录：
  - `frontend/node_modules/`
  - `story_rag_service/myenv/`
- 对 UI 改动，优先做受影响页面/流程的针对性人工验证。

## 架构速览

### 前端
- 应用栈：Vue + Pinia + Vue Router + TanStack Query。
- 故事主页面：`frontend/src/views/StoryView.vue`。
- 故事链路核心文件：
  - `frontend/src/domains/story/api/storyGenerationApi.ts`
  - `frontend/src/services/schemas.ts`
  - `frontend/src/stores/storySession.ts`

### 后端
- 应用启动：`story_rag_service/main.py` 初始化数据库、用户管理与服务容器。
- v2 API 入口汇总：`story_rag_service/api/v2/__init__.py`。
- 非流式生成：走 `graph/story_v2/runtime.py` + `graph/story_v2/nodes.py`。
- 流式生成：仍走 `services/story_generator.py` 的 SSE 链路。
- 运行时持久化：以 SQLite 为中心，配置由 `story_rag_service/config.py` 统一管理。

## 变更实践建议
- 涉及故事生成时，要同时核对前后端契约：
  - 前端类型/解析
  - 后端 schema/route
  - 图节点或生成服务实现
- 改动 SSE 载荷时，必须同步检查：
  - 前端流解析器：`frontend/src/domains/story/api/storyGenerationApi.ts`
  - 后端流封装：`story_rag_service/api/v2/story/generation_routes.py`
- 仓库检索时尽量排除 vendor/生成目录，减少噪音。
- 任何涉及故事主链路的改动，严禁只改前端或只改后端一侧。
- 一旦发生变更，必须同步更新 `PROJECT_STRUCTURE.md`。

## Agent 约束
1. 优先做小而聚焦的改动，避免无关重构。
2. 以代码现状为准，旧文档只作参考。
3. 框架行为不确定时优先查最新文档，不依赖过时经验。
4. 涉及故事主链路的改动，严禁只改前端或只改后端一侧。
