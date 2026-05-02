# 项目结构说明（前端 + 后端）

> 本文件用途：给后续 AI agent 快速建立工程上下文，每次发生变更时更新。  
> 原则：以代码现状为准，`README.md` / `AGENTS.md` / `CLAUDE.md` 仅作辅助说明；如与代码冲突，以代码为准。

## 1. 仓库总览

当前仓库目录名仍为 `AI_ChatBox`，但产品定位已经收敛为“故事设计与生成工作台”，不是通用 AI 聊天壳。

```text
AI_ChatBox/
├── frontend/                  # Vue 3 + TypeScript + Vite 前端工作台
├── story_rag_service/         # FastAPI 后端，负责故事生成、RAG、持久化、流式输出
├── doc/                       # 仓库级论文写作章节草稿与阶段性说明文档
├── README.md                  # 面向人的项目介绍
├── AGENTS.md                  # 轻量协作约束
├── CLAUDE.md                  # 更完整的仓库事实与架构说明
└── PROJECT_STRUCTURE.md       # 本文档
```

`doc/` 当前还包含第4章系统设计文档配套的 drawio 图源与 SVG 导出图，主要用于论文/PDF 排版引用：

- `chapter-01-introduction.md`：第1章绪论，说明研究背景、研究意义、研究现状、主要内容和论文结构。
- `chapter-02-related-technologies.md`：第2章相关技术介绍，围绕项目实际使用的前后端、检索增强、模型调用和数据存储技术展开。
- `chapter-03-requirements-analysis.md`：第3章需求分析，说明系统面向的用户、功能需求、非功能需求与可行性。
- `chapter-04-architecture-overview.*`：系统总体架构概览图。
- `chapter-04-architecture-overview.png`：由同名 SVG 转出的 Word 嵌入用栅格图。
- `chapter-04-persistence-strategy.*`：数据持久化策略图。
- `chapter-04-streaming-sequence.*`：流式故事生成主链路时序图。
- `chapter-04-system-design-and-implementation.md`：第4章系统设计与实现，围绕架构、接口、数据库和关键链路进行说明。
- `chapter-05-system-testing-and-validation.md`：第5章测试与验证草稿，承接第4章实现内容，聚焦基础接口烟雾测试与“上古卷轴”世界多轮故事生成验证，并记录测试所用 Lorebook 实体数据列表。
- `chapter-06-conclusion-and-outlook.md`：第6章总结与展望，总结本文工作、当前不足与后续改进方向。
- `references.md`：论文参考文献，整理自仓库根目录 `毕设参考文献/` 下的本地文献材料。
- `thesis-merged-draft.md`：第1至第6章与参考文献合并后的论文正文草稿。
- `thesis-merged-draft.docx`：由合并后的 Markdown 草稿生成的 Word 版本，正文使用宋体五号、1.5 倍行距，标题使用黑体四号/五号样式。
- `thesis-merged-draft.audit.*`：Word 草稿的 OOXML 结构审计输出，用于检查样式、标题缩进与章节设置风险。
- `thesis-merged-draft-condensed.docx`：按精简要求重写第2、3、5、6章后导出的精简版 Word 文档。
- `thesis-merged-draft-condensed.audit.*`：精简版 Word 文档的 OOXML 结构审计输出。
- `thesis-merged-draft-revised.docx`：在精简版基础上进一步调整第2、3、6章结构后的修订版 Word 文档。
- `thesis-merged-draft-revised.audit.*`：修订版 Word 文档的 OOXML 结构审计输出。
- `thesis-merged-draft-toc-optimized.docx`：进一步优化目录样式后的 Word 文档，目录章级条目为四号黑体，节级条目为五号黑体并带两格缩进。
- `thesis-merged-draft-toc-optimized.audit.*`：目录优化版 Word 文档的 OOXML 结构审计输出。
- `thesis-merged-draft-toc-paged.docx`：采用 Word 自动目录域实现页码点线对齐的版本，目录样式保持章级四号黑体、节级五号黑体并带两格缩进。
- `thesis-merged-draft-toc-paged.audit.*`：自动目录页码版 Word 文档的 OOXML 结构审计输出。
- `2026-05-01_functional-smoke-test.md`：2026-05-01 的基础功能烟雾测试记录，覆盖健康检查、认证、会话、Provider 连通性与最小故事输出闭环。

第4章核心数据 ER 图直接以内联 Mermaid 写在 `doc/chapter-04-system-design-and-implementation.md` 中，便于论文源文档维护。

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
  - 先解析登录状态，再按当前用户恢复工作区
  - 未登录或 `hideChrome` 路由不显示侧边栏
  - 仅在已登录后调用 `useConfigStore().initializeConfig()`
  - 仅在已登录后调用 `useStorySessionStore().loadFromStorage()`
- 路由入口：`frontend/src/router/index.ts`
  - `/login` 是独立登录页，使用 `publicOnly` / `hideChrome` meta
  - 登录页视觉层复用全局 `background/card/border/sidebar` 主题 token，避免与登录后工作台割裂
  - 其他工作台路由默认要求登录，守卫会保留原始 `fullPath` 作为回跳目标
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
  - `DashboardStoryMemoryView.vue`：故事记忆阅读台，主阅读路径已切到“世界 / 故事 / 每轮 prompt 的记忆变动”，基于 `story_memory.story_id + StoredStory.segments + source_turn` 把时间线事件还原到具体轮次；每轮只展示摘要化 prompt、涉及设定与关键变动，不完整倾倒原始结构。
    - 左栏已收敛成极简“选择故事”面板，只保留刷新、关键字搜索和故事卡片，不再展示复杂筛选器、总览区或会话列表分页控件。
    - 右栏会优先尝试拉取 `/stories/{story_id}` 补全轮次 prompt / `retrieved_context`；缺失 `story_id` 或 `source_turn` 时会回退到未定位事件提示，而不是伪造轮次。
    - 右栏核心阅读区已改成“单轮单页”，第几轮和用户 prompt 会被突出展示；翻页只在轮次页之间切换，不再把整段历史事件堆在同一页。
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
  - `auth.ts`：登录态、会话恢复、注册/登录/登出与 legacy 认领触发。
  - `config.ts`：Provider、模型、API Key 状态与全局配置。
    - 当前支持按登录用户重置内存态，避免切号时把前一个用户配置当作 fallback。
  - `storySession.ts`：故事会话相关快照，包含统一 `storyMemorySessionMap` 聚合记录，并兼容摘要记忆、实体状态、字段级 `entity patch`、`world_update`、记忆事件、分支树等旧结构。
    - 当前会在重新加载前先清空内存态，避免跨用户残留。
  - `storyDraftState.ts`：按故事与路由隔离的输入草稿状态。
  - `storyWorkspace.ts`：故事工作区相关状态。
- `memoryUpdateDashboard.ts`：记忆可视化页面状态。
    - 当前维护服务端事件查询条件、左栏会话定位条件、会话列表本地分页，以及右栏时间线详情分页状态；不再维护页面级时间窗口筛选。

#### `frontend/src/domains/`

- 当前前端最重要的业务分层，按功能域拆分。
- 每个域内通常继续拆为：
  - `api/`：直接发 HTTP / SSE 请求
  - `queries/`：TanStack Query 封装
  - `composables/`：页面编排与复用逻辑
  - `constants/` / `types.ts` / `utils/`：该业务域内部约定
- 已出现的核心业务域：
  - `domains/auth/`
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
  - `buildEntityNameMap(...)` 当前会同时合并实体快照、patch / 时间线以及 Lorebook 角色条目，减少同行关系回退成 UUID
- `frontend/src/domains/story/entityCompanion.ts`
  - 统一兼容实体同行关系的两种结构：旧 `UUID string` 与新 `{ id, display_name }`
  - 供故事页侧栏、dashboard 和记忆字段展示共享，优先输出角色名，回退时再显示 id
- `frontend/src/domains/story/storyMemoryPayload.ts`
  - 统一从 `story_memory` 提取摘要、实体快照、实体 patch、`world_update` 与时间线
  - 供故事页与 dashboard 共享，减少页面层重复解包逻辑
- `frontend/src/domains/story/queries/useStoryQueries.ts`
  - 提供按 `story_id` 读取单故事详情的 TanStack Query hook
  - 供记忆历史页在选中 session 后补全 `segments.prompt / retrieved_context`
- `frontend/src/domains/memory/memoryUpdatePresentation.ts`
  - 统一格式化记忆更新时间线中的 `before/after` 负载
  - 会递归展开对象与数组，输出逐字段中文 `key:value`，避免在 UI 中直接展示整段 JSON
- `frontend/src/domains/memory/storyMemoryRounds.ts`
  - 把 `StoredStory.segments` 与记忆时间线按 `source_turn` 组装成轮次视图
  - 输出 dashboard 消费的“每轮 prompt / 涉及设定 / 关键事件”摘要模型，并处理缺失 story segment 的回退态

#### `frontend/src/services/`

- 通用服务层，放跨域共享的能力，而不是某个单一业务域。
- 重点文件：
  - `api.ts`：Axios 实例、统一错误拦截与 `withCredentials` Cookie 请求模式。
  - `schemas.ts`：Zod 响应校验，尤其是 v2 生成结果契约。
  - `storyV2Api.ts`、`roleApi.ts`、`lorebookService.ts` 等：较旧或跨域共享 API。
- `frontend/src/utils/storage.ts`
  - 本地缓存按 `user_id` 作用域命名空间存储
  - 后端 `client-storage` 请求统一携带 Cookie
  - 保留旧全局 key 的一次性本地迁移兼容

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
  - 发送基于 Cookie 的认证请求
  - 解析 SSE 事件
  - 定义 TypeScript 侧契约
  - 当前 `EntityStateSnapshot.companions` 已兼容旧 `string[]` 与新 `{ id, display_name }[]`
- `useStoryGeneration.ts` 在 `choices` 模式下会对流式 chunk 做前端增量拆分：
  - 流式阶段把 `[A]/[B]/[C]` 选项从正文显示中剥离，避免污染会话输出
  - 最后一段的 `BranchChoiceCard` 会在生成中实时跟随 `seg.choices` 刷新，但保持禁用态，待生成结束后再允许点击发送
  - 无论模型实际吐出多少个候选，前后端都会在抽取层和消费层双重截断为前 3 个
- `frontend/src/domains/memory/api/memoryUpdatesApi.ts`
  - 负责查询服务端记忆 journal 与统一故事记忆快照
  - 包含 `/api/v2/story/session/{session_id}/story-memory` 对应前端调用
- `schemas.ts` 用 Zod 校验后端返回。
- `storySession.ts` 把统一故事记忆记录、摘要记忆、实体状态、`entity patch` 时间线、`world_update` 与分支树等会话级数据持久化到前端状态中。
- `storySession.ts` 的旧摘要/实体/world/timeline getter 已逐步改为优先读取统一 `storyMemorySessionMap`，旧 map 主要保留为兼容桥接与回填来源。
- `StoryMemorySidebar.vue` 产品层统一展示“故事记忆”，底层仍兼容实体快照、结构化 `world update` 与字段级 patch 时间线。
- `StoryMemorySidebar.vue` 当前会合并当前世界的 Lorebook 角色条目，补全 `companions` 的显示名，避免同行者仅显示 UUID。
- `DashboardStoryMemoryView.vue` 会聚合展示服务端 journal，并优先通过统一 `story_memory` 详情接口读取摘要、实体快照、`world_update` 与 patch 时间线；页面默认隐藏复杂标识，优先输出可读中文摘要，补充世界名显示，并为历史事件提供分页浏览与省略文本展开，`before/after` 明细默认展开为逐字段中文对比。
- `DashboardStoryMemoryView.vue` 当前不会再按时间窗口裁剪 `/memory-updates` 结果；左栏只保留极简故事定位，不再暴露复杂筛选项。
- `DashboardStoryMemoryView.vue` 左栏直接选择故事；右栏按轮次单页阅读，并继续用 `/story/session/{session_id}/memory-updates` 与 `/story/session/{session_id}/story-memory` 拉取原始事件后在前端重组成轮次页。
- `DashboardStoryMemoryView.vue` 当前也会按选中会话的 `world_id` 拉取 Lorebook 角色条目，用于补全 `companions` 显示名。

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
  - 当前已收敛为薄入口，委托 `bootstrap/app_factory.py` 创建 FastAPI app
  - 生命周期中的数据库、用户管理、服务容器初始化已开始迁移到 `bootstrap/`
- 配置入口：`story_rag_service/config.py`
  - 统一管理 API Key、默认模型、数据库路径、Chroma 路径、检索参数、LangGraph checkpoint 与认证/CORS 配置等
  - `allow_online_embedding_download` 默认关闭；本地模型缺失时会退回轻量离线嵌入以保证服务可启动

### 4.2 后端目录职责

```text
story_rag_service/
├── main.py                    # FastAPI 应用入口
├── config.py                  # pydantic-settings 配置
├── bootstrap/                 # 组合根与应用装配（进行中）
├── api/                       # 路由层与服务装配
│   ├── service_context.py     # ServiceContainer，集中装配共享服务
│   ├── dependencies/          # FastAPI 细粒度 Depends provider（进行中）
│   └── v2/                    # 当前主 API 版本
├── application/               # 应用服务层，组织跨服务业务流程
│   ├── ports/                 # application 层依赖倒置端口（进行中）
│   ├── story_memory/          # 故事记忆聚合契约与 story_memory payload builder
│   └── story_generation/      # 故事生成应用用例与 facade/helper
├── infrastructure/            # application ports 的基础设施实现（进行中）
│   ├── providers/             # 用户设置等 provider 读取适配器
│   ├── gateways/              # LLMGateway 等外部能力适配器
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
    - 当前保留为兼容桥接层
    - 真实装配逻辑已开始迁移到 `bootstrap/container.py`
  - `dependencies/`
    - 新增细粒度 Depends provider 目录
    - 当前新增 `auth.py`，负责解析 Cookie 会话对应的 `current_user`
    - 目前已开始承接故事生成、记忆查询、世界/故事、lorebook、script design、roleplay、story/session 与调整路由的依赖注入
    - 故事生成依赖中已开始注入 observability 端口适配器，而不再由 route 直接引用埋点单例
  - `v2/__init__.py`
    - 汇总 v2 路由
    - 当前包含 `auth`、`story`、`world_story`、`script_design`、`lorebook`、`roleplay`、`analytics`、`memory`、`provider`
  - `client_storage_routes.py`
    - 前端跨设备 KV 存储接口
    - 当前已改为按 `current_user.id` 做服务端隔离，不再是全局共享表
  - `v2/memory_routes.py`
    - 提供记忆更新时间线查询
    - 提供统一故事记忆快照接口 `/story/session/{session_id}/story-memory`
- `v2/story/session_routes.py` 与 `v2/world_story_routes.py` 中保留的 `entity-state` 相关接口
    - 当前定位为 compatibility bridge
    - 优先通过事件回放 / fallback 服务返回当前快照，不再代表主写路径
    - API 输出已改为响应层富化：`companions` 返回 `{ id, display_name }[]`，不再只暴露 UUID
  - `application/story_generation/`
    - 已开始承接路由与图节点共用的请求构建、graph facade、观测封装、剧情状态组装、响应映射
    - 新增 `execution.py` 与 `session_context.py` 后，图节点中的“执行生成”“读取/回写会话上下文”已进一步下沉为应用用例

#### `story_rag_service/bootstrap/`

- 后端组合根目录，负责应用工厂与分模块装配。
- 当前已开始落地：
  - `app_factory.py`
    - 创建 FastAPI app
    - 注册 lifespan、middleware、router、静态挂载
    - 当前以显式 CORS origins + `allow_credentials=True` 支持 Cookie 认证
    - 生命周期关闭阶段已通过 application graph runner 释放 Story Graph 运行时
  - `config_resolver.py`
    - 组合根层配置解析入口
    - 将全局 `settings` 解析为 bootstrap 阶段可消费的最小配置切片
    - 当前也负责解析 Story Graph 的 feature flags 与 runtime config
  - `container.py`
    - 管理 `ServiceContainer` 与初始化入口
  - `modules/core.py`
    - 数据库、用户管理、上传目录等基础装配
  - `modules/world.py`
    - world / story / lorebook / script design 基础装配
  - `modules/memory.py`
    - summary / entity / runtime / story_memory 基础装配
  - `modules/generation.py`
    - story generator / adjustment / rebuild 相关装配
    - 当前会在装配阶段把 `UserManager` 适配为 `application/ports.UserSettingsReader`
    - 并进一步装配成 `application/ports.LLMGateway`

#### `story_rag_service/api/v2/story/`

- 故事链路最核心的路由子模块。
- 重点文件：
  - `generation_routes.py`
    - 非流式生成 `/story/generate`
    - 流式生成 `/story/generate/stream`
    - 输入增强预览 `/story/input-enhancement/preview`
    - `choices` 模式的最终结果清洗与重写也在这里
    - 内部 `StoryGenerationRequest` 的拼装已下沉到 `application/story_generation/request_builder.py`
    - Session context 的读取/创建已开始复用 `application/story_generation/session_context.py`
    - 非流式成功/失败埋点已通过 application helper + observability ports 收口
    - 非流式 graph 调用已通过 `application/story_generation/graph_facade.py` 统一封装
  - `session_routes.py`
    - 会话创建、读取、回滚、重新生成等
    - 重生成路径也已复用 `application/story_generation/graph_facade.py`
    - 会话创建入口已开始复用 `application/story_generation/session_context.py`
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
    - 懒加载并缓存 LangGraph 运行时
    - 运行入口已收敛为“配置解析 + checkpointer 创建 + graph 编译结果缓存”
  - `builder.py`
    - 负责定义 Story Graph 节点顺序并完成编译
  - `checkpointer.py`
    - 负责根据 runtime config 创建 sqlite / memory checkpointer
  - `nodes.py`
    - 各节点具体实现
    - `prepare_request_node` 已复用 `application/story_generation/request_builder.py`
    - 节点取容器已改走 `bootstrap/container.py`，不再依赖 `api/service_context.py`
    - Story graph 特性开关已改走 `bootstrap/config_resolver.py`
    - `update_story_state_node` 与 `build_v2_response_node` 已进一步下沉到 application helper
    - `generate_story_node` 与 `persist_session_node` 也已分别改走 `execution.py` 与 `session_context.py`
  - `state.py`
    - 图状态定义
  - `story_graph.py`
    - 兼容导出层
    - 新代码应优先走 `application/story_generation/graph_runner.py` 与 facade，而不是继续直接依赖该文件

#### `story_rag_service/services/`

- 核心领域服务层，代码量大、职责多，是后端主工作区。
- 重点模块：
  - `story_generator.py`
    - 流式故事生成主编排
    - 仍是 SSE 路径核心
    - 也负责输入增强预览等生成辅助能力
    - 当前已接入“双路生成”中的实体 patch 后处理编排入口
    - 构造函数已支持注入 `entity_state_event_replay_service`，与 `service_context.py` 保持一致
    - 当前 LLM 客户端创建已通过 `application/ports.LLMGateway` 间接获取
  - `entity_patch_update_service.py`
    - 实体 patch 后处理编排服务
    - 串联 extractor / validator / applier / event repository / fallback rebuild
    - 当前会在返回与持久化前富化 `companions` 字段，保证 patch / memory update 中的同行关系可读
  - `entity_state_event_replay_service.py`
    - 基于 `entity_state_events` 回放当前实体快照
    - 供 rollback / rebuild / repair fallback 优先使用
  - `entity_state_fallback_service.py`
    - 封装旧 `entity_state_manager` 的 session rebuild 能力
    - 在主生成链路中只作为 fallback / repair 使用，避免继续由 `story_generator.py` 直接持有旧 rebuild 逻辑
  - `story_rag_service/entity_state_response_serializer.py`
    - 统一实体状态 API 序列化
    - 负责把内部 `companions: list[str]` 富化为响应层 `{ id, display_name }[]`
    - 也会处理 patch / memory update 负载中的同行关系字段，减少前端 UUID 兜底逻辑
  - `story_generation/`
    - `llm_factory.py`：构造模型调用能力，当前由 infrastructure gateway 间接复用
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
  - `application/ports/`
    - 新增 Protocol 端口目录
    - 先集中声明 feature flag、用户设置、LLM 网关、仓储、observability 等抽象边界
    - 当前已开始接入故事生成链路中的用户设置读取、LLM 客户端装配与 observability 依赖
  - `application/memory/`
    - 记忆更新事件、模型、provider 与 orchestrator
  - `application/story_memory/`
    - 统一“故事记忆”响应聚合契约、payload builder 与读模型服务 `StoryMemoryService`
  - `application/story_generation/`
    - 世界配置、检索、历史窗口等生成辅助编排
    - 新增 `request_builder.py`，负责把 v2 API 请求归一化为内部 `StoryGenerationRequest`
    - 同时复用于 graph payload -> `StoryGenerationRequest` 的归一化
    - 新增 `graph_facade.py`，负责封装 Story Graph 输入载荷组装与执行
    - 新增 `graph_runner.py`，负责对 application 层暴露 graph 执行与关闭入口
    - 新增 `observability.py`，负责把生成结果转换为 metrics / analytics 载荷
    - 新增 `story_state.py`，负责剧情状态派生与快照更新策略
    - 新增 `response_builder.py`，负责 graph 内部响应 -> v2 响应映射
    - 新增 `execution.py`，负责封装非流式故事生成执行用例
    - 新增 `session_context.py`，负责封装会话上下文读取/创建与回写用例
  - `world_application.py`
  - `script_design_application.py`

#### `story_rag_service/infrastructure/`

- 基础设施实现层，用于承接 application ports 的具体适配器。
- 当前已开始落地：
  - `providers/user_settings.py`
    - 把现有 `UserManager` 适配成 `application/ports.UserSettingsReader`
    - 供 LLM gateway 读取用户模型配置、API Key 与 base URL
  - `gateways/llm.py`
    - 基于现有 `services/story_generation/llm_factory.py` 实现 `application/ports.LLMGateway`
    - 由 bootstrap 装配后注入 `StoryGenerator` 与 `StoryAdjustmentService`
  - `observability.py`
    - 把 `analytics_service` 与 `metrics_recorder` 单例适配成 application ports
    - 供故事生成路由通过依赖注入获取埋点能力

#### `story_rag_service/repositories/`

- SQLite 仓储层。
- `world_repository.py`、`story_repository.py`、`script_design_repository.py`、`story_runtime_repository.py`
  - 当前已补 legacy SQLite 自愈逻辑：启动时会先检查 `owner_user_id` 是否存在，缺列则补齐，再创建 owner 相关索引，避免旧 `chatbox.db` 因索引先建而启动失败。
- 当前可见仓储包括：
  - `auth_session_repository.py`
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
- 当前新增 `auth.py`，承载登录、注册、当前用户与 legacy 认领的请求/响应模型。

#### `story_rag_service/migrations/`

- Alembic 迁移目录。
- 如果任务涉及数据库表结构，不要只改 repository / model，必须同步检查迁移。
- 当前新增 `20260426_0007_auth_owner_isolation.py`
  - 扩展 `users` 认证字段
  - 新增 `auth_sessions`
  - 为核心资源补 `owner_user_id`
  - 新增 `client_storage_entries` 复合主键表

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
  - `smoke_auth_story_runtime.py`
  - `smoke_tes_world_validation.py`
- `smoke_all_api_functional_attempt_20260410.py`
  - 基于 OpenAPI 遍历接口
  - 会先准备共享业务夹具，并对破坏性 `DELETE` 探测使用临时资源，避免后续接口因为夹具被提前删除而出现假 `404`
  - 会补齐 `segment_id`、runtime 绑定与若干业务枚举/配置类接口的有效样例，尽量把可避免的 `WARN` 压到最低
- `smoke_auth_story_runtime.py`
  - 面向登录后的真实运行链路
  - 会跑 `auth -> provider test -> worlds -> stories -> story/session -> story/generate -> stories/{id}/segments`
  - 最后直接查 SQLite 验证 owner 隔离是否正确
- `smoke_tes_world_validation.py`
  - 面向数据库现有“上古卷轴”世界的运行级验证脚本
  - 会在隔离数据库副本上自动启动本地 `uvicorn`、创建临时账号、重绑定目标 world/lorebook、执行不超过 6 轮真实故事生成
  - 会自动输出 `docs/TestResult/TESWorld_Validation_Run_*.json` 与 `TESWorld_Validation_Report_*.md`

#### `story_rag_service/docs/`

- 架构方案、实施计划、测试记录与兼容性说明目录。
- 重点文档：
  - `ARCHITECTURE_REFACTOR_PLAN.md`
    - 已落地的后端重构执行清单与阶段记录。
  - `docs/Plan/Plan_2026-04-15_后端模块化目标目录结构蓝图.md`
    - 后端后续模块化的目标目录草图与职责边界蓝图。
    - 该文档描述的是推荐目标状态，不代表当前代码已经完成对应目录迁移。

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
2. `story_rag_service/bootstrap/app_factory.py`
3. `story_rag_service/bootstrap/container.py`
4. `story_rag_service/api/v2/story/generation_routes.py`
5. `story_rag_service/api/v2/schemas.py`
6. `story_rag_service/graph/story_v2/runtime.py`
7. `story_rag_service/graph/story_v2/nodes.py`
8. `story_rag_service/services/story_generation/*`
9. `story_rag_service/repositories/*`

执行链路概括：

- FastAPI 启动先进入 `main.py`，再由 `bootstrap/app_factory.py` 创建应用并初始化容器。
- `/api/v2/story/generate` 进入 `generation_routes.py`。
- route 先通过 `application/story_generation/graph_facade.py` 组装 `request_payload` 并执行 graph。
- `graph/story_v2/runtime.py` 负责执行 LangGraph。
- 图节点在 `nodes.py` 中完成请求准备、状态更新、生成、持久化、响应构建。
- 最终由 `V2GenerateResponse` 返回给前端。

#### 流式生成

执行链路概括：

- `/api/v2/story/generate/stream` 进入 `generation_routes.py`。
- 路由层先通过 `SessionManager` 获取或创建会话上下文。
- 内部 `StoryGenerationRequest` 由 `application/story_generation/request_builder.py` 统一构建。
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
其中 `story_rag_service/docs/Plan/` 当前已包含：

- 双路生成与结构化 patch 方案文档
- 流式 OpenAI compat 风险与修复计划
- 实体状态精度提升优先级清单
- 故事记忆系统运行机制说明
- 后端模块化目标目录结构蓝图

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
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe -m uvicorn main:app --reload
..\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

### 常用 smoke 脚本

```bash
cd story_rag_service
..\.venv\Scripts\python.exe scripts/smoke_v2_only.py
..\.venv\Scripts\python.exe scripts/smoke_persistence_streaming.py
..\.venv\Scripts\python.exe scripts/smoke_story_control.py
..\.venv\Scripts\python.exe scripts/smoke_story_stream_contract.py
..\.venv\Scripts\python.exe scripts/smoke_dual_route_patch_plan_20260409.py
..\.venv\Scripts\python.exe scripts/smoke_story_memory_plan_20260410.py
..\.venv\Scripts\python.exe scripts/smoke_auth_story_runtime.py --base-url http://127.0.0.1:8001
```

## 10. 一句话总结

这个仓库当前最应该按“前端 Story 工作台 + 后端 v2 Story RAG Service + LangGraph 非流式链路 + StoryGenerator 流式链路 + SQLite/Chroma 持久化”来理解；任何涉及故事生成体验、载荷字段或状态持久化的改动，都默认需要检查前后端契约是否同时成立。
