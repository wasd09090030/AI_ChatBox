# Story RAG 重构执行清单（可直接执行）

> 2026-03-17 补注：本文中的历史聊天仓储/管理器字样属于阶段性记录。独立 AI 对话模块已在代码中删除，当前仅保留故事设计与生成主线。

## 0. 目标与范围
- 目标：提升高内聚低耦合，减少单目录文件数量，默认使用 SQLite，尽量退出 JSON 在线存储。
- 范围：`story_rag_service`（后端主线）；前端仅做 API 兼容性最小改动。
- 非目标：不做大规模 UI 重做，不引入与业务无关的新特性。

## 1. 执行原则
- 小步可回滚：每个任务单独可验证、可撤销。
- 先兼容再替换：保留兼容入口，逐步切主路径。
- 定点验证：每次仅验证受影响模块。

---

## 2. 阶段一（激进重组 + 存储收敛）

### 2.1 已落地（本轮）
- [x] 新增架构重构执行文档：`docs/ARCHITECTURE_REFACTOR_PLAN.md`
- [x] README 增加执行文档入口（见后续提交）
- [x] 新增 `.env.example`，默认 `storage_backend=sqlite`

### 2.2 进行中（本周）
- [x] **存储主路径收敛到 SQLite**
  - [x] 检查 `StoryManager`/`WorldManager`：默认 `storage_backend=sqlite`
  - [x] 仅保留 JSON 迁移读取，不作为在线主存储
  - [x] 验证 `stories`/`worlds` 的 CRUD 与跨世界删除逻辑
- [x] **API 结构收敛**
  - [x] 保留 `api/routes.py` 兼容层
  - [x] 将 v1 路由组织改为模块化（health/lorebook/story/world）
  - [x] v2 作为主演进入口，v1 继续兼容
- [x] **目录减负（高内聚）**
  - [x] `application/` 放用例编排
  - [x] `repositories/` 放存储实现
  - [x] `services/` 保留领域服务，移除跨职责杂糅逻辑

### 2.3 验收标准（DoD）
- [x] `story_rag_service` 启动成功，`/docs`、`/api/v1`、`/api/v2` 可访问
- [x] 世界/故事 CRUD 与故事生成链路通过（已通过 `RUN_LLM_SMOKE=true` 复测，v1/v2 生成链路均通过）
- [x] SQLite 为默认且唯一在线存储；JSON 仅迁移用途

### 2.4 本轮新增执行工具
- [x] 新增 smoke 脚本：`scripts/smoke_stage1.py`
- [x] 启动服务后执行：`python scripts/smoke_stage1.py`

### 2.5 最近一次执行记录
- 执行时间：2026-02-17
- 执行命令：`SMOKE_BASE_URL=http://127.0.0.1:8011 python scripts/smoke_stage1.py`
- 结果：`/health`、`/docs`、`/api/v2/health`、世界/故事 CRUD 全部通过；LLM 生成功能按预期跳过（未启用 `RUN_LLM_SMOKE`）

- 执行时间：2026-02-17
- 执行命令：`SMOKE_BASE_URL=http://127.0.0.1:8011 RUN_LLM_SMOKE=true python scripts/smoke_stage1.py`
- 结果：健康检查与世界/故事 CRUD 全部通过；`POST /story/generate` 返回 500（`No API key found for model gpt-4-turbo`），LLM 生成链路待补充可用密钥后复测。

- 执行时间：2026-02-17
- 执行命令：`DEFAULT_LLM_PROVIDER=deepseek DEFAULT_MODEL=deepseek-chat` 启动服务后，执行 `SMOKE_BASE_URL=http://127.0.0.1:8011 RUN_LLM_SMOKE=true python scripts/smoke_stage1.py`
- 结果：`/health`、`/docs`、`/api/v2/health`、世界/故事 CRUD、`/api/v1/story/generate`、`/api/v2/story/generate` 全部通过，阶段一验收完成。

---

## 3. 阶段二（去耦与标准化）

### 3.1 数据访问统一
- [x] 用户与阶段性聊天模块曾对齐 repository 模式（避免 manager 直写 SQL）
- [x] 引入迁移机制（Alembic）管理 schema 演进

### 3.2 领域边界清晰化
- [x] 将 World 与 Lorebook/RAG 注入的耦合行为拆为应用层用例
- [x] 路由层只做协议适配，不包含业务编排

### 3.3 可观测性基础
- [x] 增加请求级日志字段（request_id/session_id/world_id）
- [x] 为关键链路埋点（生成耗时、检索命中数、异常率）

### 3.5 阶段二启动记录
- 执行时间：2026-02-17
- 启动内容：v2 路由移除降级分支，强制全程走 graph；新增请求级日志字段（`request_id/session_id/world_id`）
- 当前状态：阶段二已启动，`user/chat` 已完成 repository 化，v2 已打通 Async SQLite checkpointer（`langgraph_checkpoints.db`）。

- 执行时间：2026-02-17
- 执行内容（历史记录）：曾新增用户与聊天仓储层，用户/聊天管理器去除直写 SQL；安装并启用 `langgraph-checkpoint-sqlite`，v2 graph 使用 `AsyncSqliteSaver`。其中独立聊天模块已于 2026-03-17 删除。
- 验证结果：`RUN_LLM_SMOKE=true` 下 `v1/v2` 生成链路通过，日志显示 `Using LangGraph SQLite checkpointer`，无路由降级。

- 执行时间：2026-02-17
- 执行内容：新增 `services/observability.py`，在 `api/v1/story_generation_routes.py` 与 `api/v2/story_routes.py` 接入结构化指标日志（生成耗时、检索命中、异常率）。
- 验证结果：`RUN_LLM_SMOKE=true` 下 `v1/v2` 指标日志输出正常（`metric=story_generation`，含 `error_rate`）。

- 执行时间：2026-02-17
- 执行内容：新增 `application/world_application.py` 统一编排 `World + Lorebook + Story` 跨域行为；`services/world_manager.py` 收敛为纯存储职责；`api/v1/world_routes.py` 改为仅协议适配。
- 验证结果：`RUN_LLM_SMOKE=true` 下世界/故事 CRUD 与 `v1/v2` 生成链路通过。

- 执行时间：2026-02-17
- 执行内容：新增 Alembic 迁移骨架（`alembic.ini`、`migrations/`、baseline revision），并在 README 增加迁移命令；现有库采用 `stamp head` 接入基线。
- 验证结果：`alembic current` 显示 `20260217_0001 (head)`。

- 执行时间：2026-02-17
- 执行内容：新增 `docs/API_COMPATIBILITY_POLICY.md`，并在中间件为 `/api/v1/*` 响应注入 `X-API-Lifecycle` / `X-API-Preferred` 头。
- 验证结果：API 生命周期策略文档化并可在响应头感知。

- 执行时间：2026-02-18
- 执行内容：启动 v1 兼容层退场（新增 `docs/V1_DECOMMISSION_PLAN.md`）；主程序切换为 v2-only 路由注册；新增 `scripts/smoke_v2_only.py`。
- 验证结果：对外仅暴露 `/api/v2/*`，可通过 v2 smoke 脚本验证。

### 3.4 验收标准（DoD）
- [x] 模块边界文档完成，跨层依赖减少
- [x] 关键路径具备可观测数据
- [x] API 兼容策略明确（v1 生命周期声明）

---

## 4. 每日执行模板（建议）
- [ ] 选择一个任务（不超过 2 小时）
- [ ] 改动前记录影响面与回滚点
- [ ] 完成后执行定点验证
- [ ] 更新本清单状态与风险备注

## 5. 风险与回滚
- 风险：v1/v2 双栈期间行为不一致。
  - 回滚：保留兼容层，出现问题时切回 v1 主路径。
- 风险：JSON 迁移遗漏导致数据缺失。
  - 回滚：保留迁移脚本与只读 JSON 快照，先比对后切换。

## 6. 当前下一步（建议按顺序执行）
1. 前端重构仅对接 `/api/v2/*`，移除所有 `/api/v1/*` 调用。
2. 使用 `python scripts/smoke_v2_only.py` 做回归（已通过）。
3. 删除仓库中的 `api/v1/*` 与 `api/routes.py`（已完成）。
4. 对外发布 v1 下线公告与接口迁移对照表。
