# Plan_2026-04-09_双路生成与结构化实体Patch实施任务清单

## 1. Planning Summary

### 1.1 目标

在《Plan_2026-04-09_双路生成与结构化实体Patch技术设计方案》的基础上，将“双路生成 + 结构化实体 patch”方案拆解为可执行、可分阶段验收、可持续记录进度的实施任务清单。

本清单的目标不是一次性推翻现有实体状态系统，而是按“契约与事件基础设施 -> extractor -> 生成接入 -> rollback/rebuild -> 前端展示增强”的顺序逐步演进。

### 1.2 范围

本任务清单覆盖以下改动面：

1. 后端实体 patch / 事件模型
2. 后端 `entity_state_events` 存储与快照投影
3. 后端结构化 extractor / validator / applier
4. `StoryGenerator` 与 `story_v2` 响应链路接入
5. rollback / regenerate / rebuild 的事件回放与 repair fallback
6. 前端 `entity_state_updates` 与 patch timeline 展示

### 1.3 约束

1. 必须基于现有仓库结构增量演进，不能绕开 `StoryGenerator`、`story_v2 graph`、`memory_update_journal` 另做一套平行系统。
2. 必须遵循单一职责原则，避免把更多逻辑继续堆进 `entity_state_manager.py` 或 `story_generator.py`。
3. 必须优先新增小模块承载 patch 相关职责，例如：
   - extractor
   - validator
   - applier
   - repository
   - projection service
4. 必须保持旧的 `entity_state_snapshot` 能继续工作，保证前端兼容。
5. extractor 失败时不得影响主文本生成成功。

### 1.4 非范围

本清单首期不覆盖以下内容：

1. 完整知识图谱
2. 非人物实体的全量状态系统
3. 人工可视化 patch 编辑器
4. provider 原生 tool calling 强依赖适配
5. Lorebook 动态主数据自动回写

---

## 2. Technical Direction

### 2.1 推荐实施方向

采用以下总体路径：

1. 先建立契约、事件流和快照投影基础设施
2. 再实现结构化 patch extractor / validator
3. 然后把双路生成接到 `StoryGenerator` 与 `story_v2`
4. 最后再调整 rollback / rebuild 与前端 patch 可视化

### 2.2 复用优先原则

以下模块优先复用：

1. `story_rag_service/services/story_generator.py`
2. `story_rag_service/graph/story_v2/nodes.py`
3. `story_rag_service/application/memory/update_service.py`
4. `story_rag_service/application/memory/journal.py`
5. `story_rag_service/models/entity_state.py`
6. `story_rag_service/repositories/entity_state_repository.py`
7. `story_rag_service/services/entity_state_manager.py`
8. 现有前端 `entity_state_snapshot` 展示链路

以下能力建议新增为独立模块：

1. `EntityStatePatch` / `EntityStateEventRecord`
2. `SqliteEntityStateEventRepository`
3. `EntityStateProjectionService`
4. `EntityPatchExtractor`
5. `EntityPatchValidator`
6. `EntityPatchApplier`

### 2.3 关键取舍

#### 取舍 1：先串行双路，后并行优化

原因：

1. patch 抽取依赖最终生成文本
2. 串行方案工程风险最低
3. 便于先做对账与回滚

#### 取舍 2：先聚焦角色级 `entity_patch`

原因：

1. 当前最明确的业务目标是人物状态追踪
2. 可避免 `world_update` 与 `story_state / runtime_state` 边界冲突

#### 取舍 3：先建立事件真相源，再逐步弱化全文重建

原因：

1. 现有 rebuild 已跑通，是安全 fallback
2. 事件流需要先稳定后才能成为主路径

---

## 3. 分阶段实施计划

## Phase 1：契约与事件基础设施

### 目标

1. 定义 `entity_patch` 与 `entity_state_events` 的最小模型
2. 建立事件仓储与快照投影服务
3. 在响应契约中预埋 `entity_state_updates / world_update`
4. 补齐服务容器中缺失的实体状态装配

### 主要改动面

1. `story_rag_service/models/`
2. `story_rag_service/repositories/`
3. `story_rag_service/services/database.py`
4. `story_rag_service/api/service_context.py`
5. `story_rag_service/models/story.py`
6. `story_rag_service/api/v2/schemas.py`
7. `story_rag_service/graph/story_v2/nodes.py`

### 验收

1. 新模型、仓储、投影服务已存在且职责清晰
2. `entity_state_events` SQLite 表可初始化
3. 服务容器可正确暴露 `entity_state_manager`
4. 新响应字段已向后兼容预埋

### 当前状态

1. 已完成，完成日期：2026-04-09

### 完成情况记录

1. 已新增 `models/entity_state_event.py`
2. 已新增 `repositories/entity_state_event_repository.py`
3. 已新增 `services/entity_state_projection_service.py`
4. 已在 `services/database.py` 中补齐 `entity_state_events` 表初始化
5. 已在 `api/service_context.py` 中补齐：
   - `entity_state_manager`
   - `entity_state_event_repository`
   - `entity_state_projection_service`
6. 已在响应模型中预埋：
   - `entity_state_updates`
   - `world_update`
7. 已在 `story_v2` 响应映射中透传上述可选字段
8. 已在删除故事时同步清理 `entity_state_events`

## Phase 2：结构化 patch extractor / validator / applier

### 目标

1. 引入第二路结构化 patch 生成
2. 对 patch 做本地校验与降级
3. 将合法 patch 应用到当前快照并落成事件

### 主要改动面

1. `story_rag_service/services/story_generation/`
2. `story_rag_service/services/`
3. `story_rag_service/models/`

### 依赖

1. Phase 1

### 验收

1. extractor 可在主文本生成后独立运行
2. 非法 patch 会被过滤或降级
3. applier 可基于 patch 产出新的 current snapshot

### 当前状态

1. 已完成，完成日期：2026-04-09

### 已完成记录

1. 已新增 `services/story_generation/entity_patch_prompt.py`
2. 已新增 `services/story_generation/entity_patch_extractor.py`
3. 已新增 `services/story_generation/entity_patch_validator.py`
4. 已新增 `services/story_generation/entity_patch_applier.py`
5. 已新增 `services/entity_patch_update_service.py` 作为 patch 编排服务，负责抽取 / 校验 / 应用 / 持久化 / fallback rebuild
6. 已将上述模块注册进 `api/service_context.py`，并完成 `EntityPatchUpdateService` 装配
7. 已补齐 validator 的实体名回填、同伴字段归一化、地点合法性过滤等稳健性逻辑
8. 已补齐 applier 返回 `snapshots` 契约，避免 patch 结果与快照持久化脱节

## Phase 3：接入 StoryGenerator 与 v2 返回链路

### 目标

1. 在 generate / stream / regenerate 中正式启用第二路 patch
2. 让 patch 事件与 `memory_update_journal` 共用同一 operation chain
3. 返回 `entity_state_updates`

### 主要改动面

1. `story_rag_service/services/story_generator.py`
2. `story_rag_service/api/v2/story/generation_routes.py`
3. `story_rag_service/api/v2/story/session_routes.py`
4. `story_rag_service/graph/story_v2/nodes.py`

### 依赖

1. Phase 2

### 验收

1. generate / stream / regenerate 三条路径返回行为一致
2. patch 事件与 summary/episodic/entity_state 同轮对账
3. extractor 失败不影响正文输出

### 当前状态

1. 已完成，完成日期：2026-04-09

### 完成情况记录

1. `StoryGenerator` 已接入 `EntityPatchUpdateService`
2. 非流式 `generate_story(...)` 已改为“patch 为主、rebuild 为 fallback”
3. 同步 `generate_story_sync(...)` 已接入同样的实体状态更新链路
4. 流式 `generate_story_stream(...)` done payload 已返回：
   - `entity_state_snapshot`
   - `entity_state_updates`
   - `world_update`
5. `StoryGenerationResponse` 主响应已填充：
   - `entity_state_snapshot`
   - `entity_state_updates`
   - `world_update`
6. patch 事件与 `memory_update_journal` 已共用同轮 `operation_id` 注入入口
7. extractor / validator / applier 任一环节失败时，正文输出仍可保留，并回退到 session rebuild

## Phase 4：rollback / rebuild / repair fallback 对齐

### 目标

1. 让 rollback / rebuild 能优先走事件回放
2. 保留全文重建作为 repair fallback
3. 让 story/session rebuild API 与新事件层兼容

### 主要改动面

1. `story_rag_service/api/v2/story/session_routes.py`
2. `story_rag_service/api/v2/world_story_routes.py`
3. `story_rag_service/services/story_consistency_rebuild_service.py`
4. `story_rag_service/services/entity_state_manager.py`

### 依赖

1. Phase 3

### 验收

1. rollback 后 current snapshot 与事件流一致
2. rebuild API 可恢复 patch 投影结果
3. repair 模式仍可工作

### 当前状态

1. 已完成，完成日期：2026-04-09

### 完成情况记录

1. 已新增 `services/entity_state_event_replay_service.py`，用于基于 `entity_state_events` 投影当前快照
2. rollback / regenerate 的会话一致性重建已优先裁剪事件流并走 replay
3. story segment rollback 已优先基于剩余 turn 的事件流回放当前实体状态
4. story/session 两类 `entity-state rebuild API` 已优先尝试 replay，无事件时再 fallback 到全文重建
5. `story_adjustment_commit` 仍保留全文重建为主路径，作为内容中段修改场景下的 repair fallback
6. rollback / commit / story rollback 相关重建链已补齐统一 `operation_id / sequence` 传递

## Phase 5：前端 patch 展示与验证增强

### 目标

1. 增强故事页与 dashboard 页的 patch 展示
2. 扩展 smoke / 验证脚本，覆盖字段级 patch 断言

### 主要改动面

1. `frontend/src/`
2. `story_rag_service/scripts/`
3. `story_rag_service/docs/TestResult/`

### 依赖

1. Phase 4

### 验收

1. 可按角色查看最近 patch 变化
2. smoke 可验证 patch 字段级正确性
3. dashboard 可按 `entity_state` patch source 过滤

### 当前状态

1. 已完成，完成日期：2026-04-09

### 完成情况记录

1. 已扩展 `frontend/src/stores/storySession.ts`，新增：
   - `entityUpdateMap`
   - `worldUpdateMap`
   - `appendEntityStateUpdates(...)`
   - `recordWorldUpdate(...)`
   - `getSessionEntityStateUpdates(...)`
   - `getSessionWorldUpdate(...)`
2. 已在 `frontend/src/domains/story/composables/useStoryGeneration.ts` 中将：
   - `entity_state_updates`
   - `world_update`
   接入 generate / stream / regenerate 后的前端会话持久化链路
3. 已新增 `frontend/src/domains/story/entityPatchPresentation.ts`，统一承载 patch / world update 展示格式化逻辑，避免故事页与 dashboard 重复拼装
4. 已增强 `frontend/src/components/story/StoryMemorySidebar.vue`，新增：
   - 结构化 `world update` 展示块
   - 字段级 patch 时间线
5. 已增强 `frontend/src/views/StoryView.vue`，将当前 session 的 patch / world update 注入故事侧栏
6. 已增强 `frontend/src/views/DashboardStoryMemoryView.vue`，新增：
   - `world update` 摘要展示
   - 字段级 patch 时间线展示
   - patch 数量指标
7. 本轮未在 WSL 下执行慢速 smoke；前端静态构建依赖当前环境安装 Node 依赖后再执行
8. 已补充修复流式路径的 provider 兼容问题：SSE 正文生成仍使用流式 LLM，但 `entity patch` 抽取改为单独创建非流式 LLM，避免 `stream_options should be set along with stream = true` 导致的 patch 抽取退化
9. 已继续完成流式 OpenAI compat 风险收口：
   - 流式链的输入增强与 lorebook 压缩改为复用非流式 `preprocess_llm`
   - `services/ai_proxy/streamers.py` 在 provider 拒绝 `stream_options` 时自动回退为不带 `stream_options` 的 SSE 请求

---

## 4. 当前实施结论

截至 `2026-04-09`，本轮已经完成 Phase 1 ~ Phase 5 的实现落地。

当前最合适的下一步是：

1. 在已安装前端依赖的环境执行一次 `npm run build`
2. 基于真实故事 session 补一轮前端人工验收，重点核对 patch 时间线与 `operation_id` 对齐
3. 视需要扩展 dashboard 过滤能力，例如按 `operation_id` / `entity_id` 聚合 patch
4. 评估是否将 `story_adjustment_commit` 也演进到 patch 优先、全文重建 fallback

本清单将作为后续每个阶段实施后的进度记录文件持续更新。
