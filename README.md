# 故事工坊

> 仓库目录名仍为 `AI_ChatBox`，但自 2026-03-17 起产品定位已收敛为“故事设计与生成工作台”，独立 AI 对话功能已下线。

一个面向中文创作与互动叙事的全栈 AI 应用仓库，包含前端工作台与后端 Story RAG 服务。项目的核心目标不是做一个单轮问答页面，而是提供可持续创作、可追踪上下文、可控制生成走向的故事与角色扮演基础设施。

## 项目概览

仓库由两个主要部分组成：

- `frontend/`：Vue 3 + TypeScript + Vite 的前端应用，提供故事创作、设定管理、角色扮演辅助控制、剧本设计、统计分析等界面。
- `story_rag_service/`：FastAPI 后端，负责故事生成、RAG 检索、Lorebook 管理、会话持久化、流式输出与摘要记忆。

项目当前的架构方向很明确：

- 前端按功能域拆分，减少巨型 view 文件和跨层耦合。
- 后端以 `api/v2` 为唯一对外版本，逐步收敛旧接口。
- 故事生成同时支持“生成质量”和“工程可控性”，而不是只追求单次效果。

## 这个项目解决什么问题

常见互动叙事产品的短板是：上下文不可控、世界设定容易丢、生成方向不可精细干预、长会话成本会持续飙升。这个项目围绕这些问题做了系统设计：

- 用 Lorebook + RAG 让设定能被检索、复用、隔离。
- 用多世界管理让不同创作主题互不污染。
- 用会话持久化与摘要记忆降低长篇创作劣化。
- 用 Author's Note、模式切换、Prompt 编排控制故事走向。
- 用统计分析页让用户能看到模型、事件、Token 消耗与运行趋势。

## 核心亮点

### 1. 面向创作而不是普通问答

项目的主轴是故事创作与角色扮演，不是通用 AI 对话壳子。它支持：

- 多世界故事管理
- Lorebook 世界设定注入
- 分支选项式故事推进
- 指令式强制剧情推进
- 主角人设选择与 Prompt 编排

### 2. RAG 与世界设定深度结合

项目不是简单把向量检索塞进生成接口，而是把 Lorebook 条目作为故事世界的长期知识层。角色、地点、事件会在当前世界内被检索和注入，降低世界观漂移。

### 3. 流式生成与持久化同时兼顾

很多项目只能做到“能流式返回”或“能保存结果”其中一个，这里同时做了：

- SSE 流式输出
- 会话与消息持久化
- 回滚最后一轮
- 对同一输入重新生成

这让它更接近可用的创作系统，而不是 Demo。

### 4. 有长期记忆，不是无限堆历史

项目引入了 LLM 摘要记忆机制，不是机械拼接所有历史消息，而是定期压缩长上下文，平衡质量、成本与可持续对话长度。

### 5. 前后端都在朝“可维护的大项目”方向演进

当前仓库已经在持续做模块化重构：

- 前端从“大 view + 大 service”向 `domains/**/api`、`composables`、独立组件迁移。
- 后端从单体式路由与逻辑向 `api/v2`、graph runtime、service layer 分层迁移。

这意味着它不只是“功能多”，而且在逐步变成“能长期维护”。

## 仓库结构

```text
AI_ChatBox/
├── frontend/                 # Vue 3 前端工作台
├── story_rag_service/        # FastAPI 故事生成与 RAG 后端
├── AGENTS.md                 # 仓库级开发说明
├── CLAUDE.md                 # 当前仓库补充说明
├── FRONTEND_REBUILD_PLAN.md  # 前端重构计划
└── Nginx.txt                 # 反向代理与部署备注
```

## 前端能力

前端不是简单页面集合，而是一个创作工作台，当前重点包括：

- Story 故事创作页
- Lorebook 世界与条目管理
- 剧本设计与推进控制
- Dashboard 配置管理
- Dashboard Analytics 数据统计与筛选分析

前端技术栈：

- Vue 3
- TypeScript
- Vite
- Pinia
- Vue Router
- TanStack Vue Query
- Tailwind CSS
- ECharts / vue-echarts

## 后端能力

后端以 Story RAG Service 为核心，负责：

- `/api/v2` 故事生成接口
- `/api/v2/providers*` Provider 配置与模型探测接口
- 会话创建、回滚、重新生成
- Lorebook 与世界管理
- RAG 检索与上下文拼接
- SSE 流式返回
- 摘要记忆
- 模型与 Provider 接入

后端技术栈：

- FastAPI
- Pydantic
- SQLite
- ChromaDB
- LangChain
- 多模型 Provider（OpenAI / Anthropic / DeepSeek 等）

## 快速开始

### 1. 前端

```bash
cd frontend
npm install
npm run dev
```

常用命令：

```bash
npm run build
npm run preview
npm run lint
npm run lint:fix
npm run format
```

### 2. 后端

```bash
cd story_rag_service
python -m venv myenv
myenv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

也可以使用：

```bash
uvicorn main:app --reload
```

### 3. 数据库迁移

```bash
cd story_rag_service
python -m alembic -c alembic.ini upgrade head
```

## 常用验证命令

前端构建验证：

```bash
cd frontend
npm run build
```

后端 Smoke 测试示例：

```bash
cd story_rag_service
python scripts/smoke_v2_only.py
python scripts/smoke_persistence_streaming.py
python scripts/smoke_story_control.py
python scripts/smoke_story_stream_contract.py
```

## 当前架构特点

### 前端

- 入口在 `frontend/src/main.ts`
- 路由在 `frontend/src/router/`
- 长生命周期状态主要在 `frontend/src/stores/`
- 远程调用逐步收敛到 `frontend/src/domains/**/api`
- 视图正在持续拆分成 composable + domain API + 展示组件

### 后端

- 入口在 `story_rag_service/main.py`
- API 聚合在 `story_rag_service/api/v2/`
- 服务容器在 `story_rag_service/api/service_context.py`
- 非流式故事生成走 `graph/story_v2/`
- 流式故事生成仍由 service 层和 SSE 路由负责

## 为什么这个项目值得继续做

这个项目最有价值的地方，不在于“又接了一个大模型”，而在于它把创作系统里真正难的几件事放在了一起处理：

- 长期上下文管理
- 世界设定隔离与检索
- 流式体验与持久化并存
- 生成方向可控
- 前后端契约逐步工程化

很多项目只做到了其中一个点，而这个仓库已经把这些能力串成了一个完整闭环。

## 进一步阅读

- `frontend/README.md`：前端子项目说明（当前仍较简略，后续可继续补充）
- `story_rag_service/README.md`：后端 Story RAG 服务详细说明
- `story_rag_service/docs/ARCHITECTURE_REFACTOR_PLAN.md`：后端架构重构计划
- `FRONTEND_REBUILD_PLAN.md`：前端重构规划
- `AGENTS.md`：仓库级开发与结构约定
