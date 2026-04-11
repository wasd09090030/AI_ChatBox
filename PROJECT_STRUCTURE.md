# 项目结构说明（前端 + 后端）

> 本文件用途：给后续 AI agent 快速建立工程上下文，每次发生变更时更新。  
> 原则：以代码现状为准，`README.md` / `AGENTS.md` / `CLAUDE.md` 仅作辅助说明；如与代码冲突，以代码为准。

## 1. 仓库总览

当前仓库目录名仍为 `AI_ChatBox`，但产品定位已经收敛为“故事设计与生成工作台”，不是通用 AI 聊天壳。

```text
AI_ChatBox/
├── frontend/                  # Vue 3 + TypeScript + Vite 前端工作台
├── story_rag_service/         # FastAPI 后端，负责故事生成、RAG、持久化、流式输出
├── README.md                  # 面向人的项目介绍
├── AGENTS.md                  # 轻量协作约束
├── CLAUDE.md                  # 更完整的仓库事实与架构说明
└── PROJECT_STRUCTURE.md       # 本文档
```

## 2. 协作判断基线

- 当前主对外 API 版本是 `story_rag_service/api/v2/`。
- 故事主链路相关改动通常要联动前后端，不要只改一侧。
- “故事生成”至少要同时核对以下位置：
  - 前端请求与流解析：`frontend/src/domains/story/api/storyGenerationApi.ts`
  - 前端响应校验：`frontend/src/services/schemas.ts`
  - 后端请求/响应 schema：`story_rag_service/api/v2/schemas.py`
  - 后端路由与执行链路：`story_rag_service/api/v2/story/generation_routes.py`
- SSE 载荷调整必须联动前后端：
  - 前端：`frontend/src/domains/story/api/storyGenerationApi.ts`
  - 后端：`story_rag_service/api/v2/story/generation_routes.py`

## 3. 前端结构

### 3.1 技术栈与运行入口

- 技术栈：Vue 3、TypeScript、Vite、Pinia、Vue Router、TanStack Vue Query、Tailwind CSS、Zod。
- 应用入口：`frontend/src/main.ts`
  - 创建 Vue app
  - 注册 Pinia
  - 注册 Vue Router
  - 注册 TanStack Query
- 应用壳层：`frontend/src/App.vue`
  - 挂载左侧导航 `AppSidebar`
  - 挂载 `RouterView`
  - 在 `onMounted` 时初始化配置与故事会话状态
  - 调用 `useConfigStore().initializeConfig()`
  - 调用 `useStorySessionStore().loadFromStorage()`
- 路由入口：`frontend/src/router/index.ts`
  - `/story/improv` 和 `/story/scripted` 共用 `StoryView.vue`
  - `story-adjustment` 对应独立故事调整页
  - `/dashboard/*` 和 `/console/*` 是后台/控制台入口

### 3.2 前端目录职责

```text
frontend/
├── src/
│   ├── main.ts                # 应用入口
│   ├── App.vue                # 应用壳层与初始化
│   ├── router/                # 路由表
│   ├── app/                   # QueryClient 等应用级装配
│   ├── views/                 # 页面级视图
│   ├── stores/                # Pinia 长生命周期状态
│   ├── domains/               # 按业务域组织的 API / queries / composables
│   ├── components/            # 可复用 UI 与业务组件
│   ├── services/              # 通用 HTTP、schema、跨域公共服务
│   ├── config/                # 前端配置常量与 prompt 模板
│   ├── utils/                 # 工具函数与 storage 封装
│   ├── lib/                   # 较底层通用函数
│   └── style.css              # 全局样式入口
├── docs/                      # 前端重构研究与蓝图
├── package.json               # 前端命令与依赖
└── vite.config.ts             # Vite 配置
```

### 3.3 前端关键目录说明

#### `frontend/src/views/`

- 页面级入口层。
- 重点文件：
  - `StoryView.vue`：故事主页面，`improv` / `scripted` 两种创作模式共用。
  - `StoryAdjustmentView.vue`：故事文本调整页面。
  - `DashboardLorebookView.vue`：Lorebook 管理台。
  - `DashboardScriptDesignView.vue`：剧本设计管理页。
  - `DashboardStoryMemoryView.vue`：故事记忆阅读台，按“当前状态 / 本轮变化 / 历史翻页”组织会话信息，并补充世界名映射、前后对比卡与省略文本展开。
  - `views/console/*`：模型管理、模型选择、分析看板。

#### `frontend/src/components/`

- 组件层，按 UI 角色进一步拆分。
- 常见子目录：
  - `components/story/`：故事页侧栏、对话列表、控制面板、分支树、记忆区等。
  - `components/script-design/`：剧本设计编辑器与概览卡片。
  - `components/lorebook/`：世界书与条目编辑。
  - `components/config/`：Provider / 模型配置面板。
  - `components/layout/`：应用壳层布局。
  - `components/ui/`：基础 UI 组件封装。

#### `frontend/src/stores/`

- Pinia 状态中心，负责本地长生命周期状态。
- 重点文件：
  - `config.ts`：Provider、模型、API Key 状态与全局配置。
  - `storySession.ts`：故事会话相关快照，包含统一 `storyMemorySessionMap` 聚合记录，并兼容摘要记忆、实体状态、字段级 `entity patch`、`world_update`、记忆事件、分支树等旧结构。
  - `storyDraftState.ts`：按故事与路由隔离的输入草稿状态。
  - `storyWorkspace.ts`：故事工作区相关状态。
  - `memoryUpdateDashboard.ts`：记忆可视化页面状态。

#### `frontend/src/domains/`

- 当前前端最重要的业务分层，按功能域拆分。
- 每个域内通常继续拆为：
  - `api/`：直接发 HTTP / SSE 请求
  - `queries/`：TanStack Query 封装
  - `composables/`：页面编排与复用逻辑
  - `constants/` / `types.ts` / `utils/`：该业务域内部约定
- 已出现的核心业务域：
  - `domains/story/`
  - `domains/lorebook/`
  - `domains/memory/`
  - `domains/roleplay/`
  - `domains/role/`
  - `domains/settings/`
  - `domains/analytics/`
  - `domains/user/`
- `frontend/src/domains/story/entityPatchPresentation.ts`
  - 统一格式化 `entity_state_updates` / `world_update` 的展示文案
  - 供故事页侧栏与 dashboard 共享，避免重复实现 patch 展示逻辑
- `frontend/src/domains/story/storyMemoryPayload.ts`
  - 统一从 `story_memory` 提取摘要、实体快照、实体 patch、`world_update` 与时间线
  - 供故事页与 dashboard 共享，减少页面层重复解包逻辑

#### `frontend/src/services/`

- 通用服务层，放跨域共享的能力，而不是某个单一业务域。
- 重点文件：
  - `api.ts`：Axios 实例与统一错误拦截。
  - `schemas.ts`：Zod 响应校验，尤其是 v2 生成结果契约。
  - `storyV2Api.ts`、`roleApi.ts`、`lorebookService.ts` 等：较旧或跨域共享 API。

### 3.4 前端故事主链路

推荐按下面顺序阅读故事相关代码：

1. `frontend/src/router/index.ts`
2. `frontend/src/views/StoryView.vue`
3. `frontend/src/domains/story/composables/useStoryGeneration.ts`
4. `frontend/src/domains/story/api/storyGenerationApi.ts`
5. `frontend/src/services/schemas.ts`
6. `frontend/src/stores/storySession.ts`
7. `frontend/src/components/story/*`

链路概括：

- 路由把 `/story/improv` 与 `/story/scripted` 指向 `StoryView.vue`。
- `StoryView.vue` 负责页面级编排，组合故事库、Prompt 编排、生成控制、记忆侧栏等模块。
- `useStoryGeneration.ts` 等 composable 负责把 UI 行为组织成请求参数。
- `storyGenerationApi.ts` 负责：
  - 构造 `/api/v2/story/generate` 与 `/api/v2/story/generate/stream` 请求
  - 发送 `X-User-ID`
  - 解析 SSE 事件
  - 定义 TypeScript 侧契约
- `frontend/src/domains/memory/api/memoryUpdatesApi.ts`
  - 负责查询服务端记忆 journal 与统一故事记忆快照
  - 包含 `/api/v2/story/session/{session_id}/story-memory` 对应前端调用
- `schemas.ts` 用 Zod 校验后端返回。
- `storySession.ts` 把统一故事记忆记录、摘要记忆、实体状态、`entity patch` 时间线、`world_update` 与分支树等会话级数据持久化到前端状态中。
- `storySession.ts` 的旧摘要/实体/world/timeline getter 已逐步改为优先读取统一 `storyMemorySessionMap`，旧 map 主要保留为兼容桥接与回填来源。
- `StoryMemorySidebar.vue` 产品层统一展示“故事记忆”，底层仍兼容实体快照、结构化 `world update` 与字段级 patch 时间线。
- `DashboardStoryMemoryView.vue` 会聚合展示服务端 journal，并优先通过统一 `story_memory` 详情接口读取摘要、实体快照、`world_update` 与 patch 时间线；页面默认隐藏复杂标识，优先输出可读中文摘要，补充世界名显示，并为历史事件提供分页浏览与省略文本展开。

### 3.5 前端高频改动落点

如果任务是以下类型，优先看这些位置：

- 改故事生成 UI：
  - `frontend/src/views/StoryView.vue`
  - `frontend/src/components/story/*`
- 改故事请求参数：
  - `frontend/src/domains/story/api/storyGenerationApi.ts`
  - `frontend/src/domains/story/composables/*`
- 改响应字段或 SSE 事件：
  - `frontend/src/domains/story/api/storyGenerationApi.ts`
  - `frontend/src/services/schemas.ts`
  - `frontend/src/stores/storySession.ts`
- 改模型与提供商配置：
  - `frontend/src/stores/config.ts`
  - `frontend/src/components/config/*`
- 改世界书 / 剧本设计页面：
  - `frontend/src/domains/lorebook/*`
  - `frontend/src/components/lorebook/*`
  - `frontend/src/components/script-design/*`

## 4. 后端结构

### 4.1 技术栈与运行入口

- 技术栈：FastAPI、Pydantic、SQLite、ChromaDB、LangGraph、LangChain、多 Provider LLM 接入。
- 应用入口：`story_rag_service/main.py`
  - 建立 FastAPI app
  - 在 lifespan 中初始化数据库、用户管理、服务容器
  - 注册 `/api/v2` 路由
  - 挂载上传文件静态目录
- 配置入口：`story_rag_service/config.py`
  - 统一管理 API Key、默认模型、数据库路径、Chroma 路径、检索参数、LangGraph checkpoint 等
  - `allow_online_embedding_download` 默认关闭；本地模型缺失时会退回轻量离线嵌入以保证服务可启动

### 4.2 后端目录职责

```text
story_rag_service/
├── main.py                    # FastAPI 应用入口
├── config.py                  # pydantic-settings 配置
├── api/                       # 路由层与服务装配
│   ├── service_context.py     # ServiceContainer，集中装配共享服务
│   └── v2/                    # 当前主 API 版本
├── application/               # 应用服务层，组织跨服务业务流程
│   ├── story_memory/          # 故事记忆聚合契约与 story_memory payload builder
├── graph/story_v2/            # LangGraph 图编排
├── services/                  # 核心领域服务与基础设施服务
├── repositories/              # SQLite 仓储层
├── models/                    # Pydantic / 领域模型
├── migrations/                # Alembic 迁移
├── scripts/                   # Smoke / 验证脚本
├── docs/                      # 方案、验证记录、变更说明
├── data/                      # 运行时数据（SQLite、Chroma、缓存、上传文件）
└── requirements.txt           # Python 依赖
```

### 4.3 后端关键目录说明

#### `story_rag_service/api/`

- 路由层与依赖装配层。
- 重点文件：
  - `service_context.py`
    - 创建 `ServiceContainer`
    - 装配 `StoryGenerator`、`StoryManager`、`WorldApplicationService`、`StoryRuntimeManager` 等
    - 为路由层与图执行层提供共享服务
  - `v2/__init__.py`
    - 汇总 v2 路由
    - 当前包含 `story`、`world_story`、`script_design`、`lorebook`、`roleplay`、`analytics`、`memory`、`provider`
  - `v2/memory_routes.py`
    - 提供记忆更新时间线查询
    - 提供统一故事记忆快照接口 `/story/session/{session_id}/story-memory`
  - `v2/story/session_routes.py` 与 `v2/world_story_routes.py` 中保留的 `entity-state` 相关接口
    - 当前定位为 compatibility bridge
    - 优先通过事件回放 / fallback 服务返回当前快照，不再代表主写路径

#### `story_rag_service/api/v2/story/`

- 故事链路最核心的路由子模块。
- 重点文件：
  - `generation_routes.py`
    - 非流式生成 `/story/generate`
    - 流式生成 `/story/generate/stream`
    - 输入增强预览 `/story/input-enhancement/preview`
    - `choices` 模式的最终结果清洗与重写也在这里
  - `session_routes.py`
    - 会话创建、读取、回滚、重新生成等
  - `adjustment_routes.py`
    - 故事调整相关接口
  - `health_routes.py`
    - 健康检查类接口

#### `story_rag_service/api/v2/schemas.py`

- v2 API 的 Pydantic 契约定义。
- 前端 `frontend/src/domains/story/api/storyGenerationApi.ts` 和 `frontend/src/services/schemas.ts` 必须与这里保持一致。

#### `story_rag_service/graph/story_v2/`

- 非流式故事生成的图编排层。
- 重点文件：
  - `runtime.py`
    - 懒加载并编译 LangGraph
    - 组织节点顺序：
      - `prepare_request`
      - `update_story_state`
      - `generate_story`
      - `persist_session`
      - `build_response`
  - `nodes.py`
    - 各节点具体实现
  - `state.py`
    - 图状态定义
  - `story_graph.py`
    - 兼容导出层

#### `story_rag_service/services/`

- 核心领域服务层，代码量大、职责多，是后端主工作区。
- 重点模块：
  - `story_generator.py`
    - 流式故事生成主编排
    - 仍是 SSE 路径核心
    - 也负责输入增强预览等生成辅助能力
    - 当前已接入“双路生成”中的实体 patch 后处理编排入口
    - 构造函数已支持注入 `entity_state_event_replay_service`，与 `service_context.py` 保持一致
  - `entity_patch_update_service.py`
    - 实体 patch 后处理编排服务
    - 串联 extractor / validator / applier / event repository / fallback rebuild
  - `entity_state_event_replay_service.py`
    - 基于 `entity_state_events` 回放当前实体快照
    - 供 rollback / rebuild / repair fallback 优先使用
  - `entity_state_fallback_service.py`
    - 封装旧 `entity_state_manager` 的 session rebuild 能力
    - 在主生成链路中只作为 fallback / repair 使用，避免继续由 `story_generator.py` 直接持有旧 rebuild 逻辑
  - `story_generation/`
    - `llm_factory.py`：构造模型调用能力
    - `prompt_builder.py`：Prompt 组装
    - `context_helpers.py`：检索与上下文拼装辅助
    - `summary_helpers.py`：摘要相关辅助逻辑
    - `entity_patch_prompt.py`：结构化 patch 抽取提示词
    - `entity_patch_extractor.py`：第二路结构化 patch 抽取
    - `entity_patch_validator.py`：patch 校验与归一化
    - `entity_patch_applier.py`：patch -> 事件 / 快照应用
  - `story_manager.py`
    - 故事本体持久化与读取
  - `session_manager.py`
    - 会话上下文获取与创建
  - `story_runtime_manager.py`
    - 剧情运行态持久化与读取
  - `summary_memory_manager.py`
    - 摘要记忆更新
  - `entity_state_manager.py`
    - 实体状态跟踪
  - `lorebook_manager.py`
    - 世界设定管理与检索对接
  - `vector_store/`
    - 启动时优先读取 `data/huggingface_cache/` 本地模型
    - 若本地模型缺失且未开启在线下载，会使用轻量离线嵌入兜底，保证 FastAPI 可启动
    - 向量存储抽象
  - `ai_proxy/`
    - Provider 注册与流式封装
    - `streamers.py` 已加入 `stream_options` 被拒绝时的自动回退，提升 OpenAI-compatible / custom provider 的兼容性

#### `story_rag_service/application/`

- 应用服务层，负责跨多个 service / repository 的业务编排。
- 重点目录：
  - `application/memory/`
    - 记忆更新事件、模型、provider 与 orchestrator
  - `application/story_memory/`
    - 统一“故事记忆”响应聚合契约、payload builder 与读模型服务 `StoryMemoryService`
  - `application/story_generation/`
    - 世界配置、检索、历史窗口等生成辅助编排
  - `world_application.py`
  - `script_design_application.py`

#### `story_rag_service/repositories/`

- SQLite 仓储层。
- 当前可见仓储包括：
  - `story_repository.py`
  - `story_session_repository.py`
  - `story_runtime_repository.py`
  - `script_design_repository.py`
  - `entity_state_repository.py`
  - `entity_state_event_repository.py`
  - `world_repository.py`
  - `user_repository.py`

#### `story_rag_service/models/`

- 领域模型与存储结构模型。
- 包括故事、世界、Lorebook、角色扮演、运行态、剧本设计、实体状态、实体 patch / 事件流等模型定义。

#### `story_rag_service/migrations/`

- Alembic 迁移目录。
- 如果任务涉及数据库表结构，不要只改 repository / model，必须同步检查迁移。

#### `story_rag_service/scripts/`

- 目前最接近“自动化验证”的是这些 smoke 脚本。
- 常用脚本：
  - `smoke_v2_only.py`
  - `smoke_persistence_streaming.py`
  - `smoke_story_control.py`
  - `smoke_story_stream_contract.py`
  - `smoke_summary_memory.py`
  - `smoke_dual_route_patch_plan_20260409.py`
  - `smoke_story_memory_plan_20260410.py`
  - `smoke_all_api_functional_attempt_20260410.py`
- `smoke_all_api_functional_attempt_20260410.py`
  - 基于 OpenAPI 遍历接口
  - 会先准备共享业务夹具，并对破坏性 `DELETE` 探测使用临时资源，避免后续接口因为夹具被提前删除而出现假 `404`
  - 会补齐 `segment_id`、runtime 绑定与若干业务枚举/配置类接口的有效样例，尽量把可避免的 `WARN` 压到最低

#### `story_rag_service/data/`

- 运行时数据目录，不是业务源码。
- 常见内容：
  - `chatbox.db`
  - `chroma_db/`
  - `huggingface_cache/`
  - `FileUpload/`
- 一般排查问题时可以读，但不应当把这里当成要改的业务代码。

### 4.4 后端故事主链路

#### 非流式生成

读取顺序建议：

1. `story_rag_service/main.py`
2. `story_rag_service/api/service_context.py`
3. `story_rag_service/api/v2/story/generation_routes.py`
4. `story_rag_service/api/v2/schemas.py`
5. `story_rag_service/graph/story_v2/runtime.py`
6. `story_rag_service/graph/story_v2/nodes.py`
7. `story_rag_service/services/story_generation/*`
8. `story_rag_service/repositories/*`

执行链路概括：

- FastAPI 启动时在 `main.py` 中初始化 `ServiceContainer`。
- `/api/v2/story/generate` 进入 `generation_routes.py`。
- 路由层组装请求并调用 `run_story_graph(...)`。
- `graph/story_v2/runtime.py` 负责执行 LangGraph。
- 图节点在 `nodes.py` 中完成请求准备、状态更新、生成、持久化、响应构建。
- 最终由 `V2GenerateResponse` 返回给前端。

#### 流式生成

执行链路概括：

- `/api/v2/story/generate/stream` 进入 `generation_routes.py`。
- 路由层先通过 `SessionManager` 获取或创建会话上下文。
- 然后构造 `StoryGenerationRequest`。
- 调用 `services.story_generator.generate_story_stream(...)`。
- 路由层使用 `StreamingResponse` 输出 SSE。
- 若是 `choices` 模式，路由层会对最终 done 事件做一次选项提取与正文重写。

## 5. 前后端契约对应关系

### 5.1 故事生成契约

- 前端请求与类型：
  - `frontend/src/domains/story/api/storyGenerationApi.ts`
- 前端响应校验：
  - `frontend/src/services/schemas.ts`
- 后端请求与响应 schema：
  - `story_rag_service/api/v2/schemas.py`
- 后端路由：
  - `story_rag_service/api/v2/story/generation_routes.py`

### 5.2 SSE 契约

- 前端流解析：
  - `frontend/src/domains/story/api/storyGenerationApi.ts`
- 后端流封装：
  - `story_rag_service/api/v2/story/generation_routes.py`
- 真正的流式生成器：
  - `story_rag_service/services/story_generator.py`

### 5.3 模型与 Provider 配置

- 前端配置状态与 UI：
  - `frontend/src/stores/config.ts`
  - `frontend/src/components/config/*`
- 后端默认配置与 provider 路由：
  - `story_rag_service/config.py`
  - `story_rag_service/api/v2/provider_routes.py`
  - `story_rag_service/api/v2/provider_schemas.py`

### 5.4 记忆 / 实体状态

- 前端展示与缓存：
  - `frontend/src/stores/storySession.ts`
  - `frontend/src/domains/story/entityPatchPresentation.ts`
  - `frontend/src/components/story/StoryMemorySidebar.vue`
  - `frontend/src/views/DashboardStoryMemoryView.vue`
  - `frontend/src/domains/memory/*`
- 后端编排与输出：
  - `story_rag_service/application/story_memory/*`
  - `story_rag_service/application/memory/*`
  - `story_rag_service/services/summary_memory_manager.py`
  - `story_rag_service/services/entity_state_manager.py`
  - `story_rag_service/services/entity_patch_update_service.py`
  - `story_rag_service/services/entity_state_projection_service.py`
  - `story_rag_service/api/v2/memory_routes.py`

## 6. 建议的 AI Agent 阅读顺序

### 6.1 如果任务是“故事主流程”

1. 读 `frontend/src/router/index.ts`
2. 读 `frontend/src/views/StoryView.vue`
3. 读 `frontend/src/domains/story/api/storyGenerationApi.ts`
4. 读 `frontend/src/services/schemas.ts`
5. 读 `story_rag_service/api/v2/story/generation_routes.py`
6. 读 `story_rag_service/api/v2/schemas.py`
7. 读 `story_rag_service/graph/story_v2/runtime.py`
8. 再按需要深入 `nodes.py`、`story_generator.py`、`services/story_generation/*`

### 6.2 如果任务是“世界书 / 剧本设计”

1. 前端看 `domains/lorebook/*`、`components/lorebook/*`、`components/script-design/*`
2. 后端看 `api/v2/lorebook_routes.py`、`api/v2/script_design_routes.py`
3. 再看 `application/world_application.py`、`application/script_design_application.py`
4. 最后下沉到 `repositories/*` 与相关 `models/*`

### 6.3 如果任务是“模型配置 / Provider 管理”

1. 前端看 `stores/config.ts` 与 `components/config/*`
2. 后端看 `config.py`
3. 再看 `api/v2/provider_routes.py` 与 `services/ai_proxy/*`

## 7. 当前仓库中的“辅助但非主线”目录

以下目录存在，但通常不是当前故事主链路的第一阅读目标：

- `story_rag_service/api/ai_chat/`
- `story_rag_service/api/v2/chat/`
- `story_rag_service/repositories/chat_repository/`
- `frontend/docs/`
- `story_rag_service/docs/`

这些内容是历史兼容、设计方案或验证记录。需要追根溯源时再进入，不建议作为第一入口。
其中 `story_rag_service/docs/plan/` 当前已包含：

- 双路生成与结构化 patch 方案文档
- 流式 OpenAI compat 风险与修复计划
- 实体状态精度提升优先级清单

## 8. 检索与排噪建议

推荐优先排除以下目录，避免把第三方或运行时内容误当成主业务代码：

- `frontend/node_modules/`
- `story_rag_service/myenv/`
- `story_rag_service/data/`
- `story_rag_service/__pycache__/`

## 9. 常用启动与验证命令

### 前端

```bash
cd frontend
npm install
npm run dev
npm run build
npm run lint
```

### 后端

```bash
cd story_rag_service
pip install -r requirements.txt
uvicorn main:app --reload
python -m alembic -c alembic.ini upgrade head
```

### 常用 smoke 脚本

```bash
cd story_rag_service
python scripts/smoke_v2_only.py
python scripts/smoke_persistence_streaming.py
python scripts/smoke_story_control.py
python scripts/smoke_story_stream_contract.py
python scripts/smoke_dual_route_patch_plan_20260409.py
python scripts/smoke_story_memory_plan_20260410.py
```

## 10. 一句话总结

这个仓库当前最应该按“前端 Story 工作台 + 后端 v2 Story RAG Service + LangGraph 非流式链路 + StoryGenerator 流式链路 + SQLite/Chroma 持久化”来理解；任何涉及故事生成体验、载荷字段或状态持久化的改动，都默认需要检查前后端契约是否同时成立。
