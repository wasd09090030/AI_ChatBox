# Plan0410 故事记忆系统合并 Smoke 验证报告

## 1. 验证目标

依据 `Plan_2026-04-10_故事记忆系统合并实施任务清单.md`，验证后端 Story Memory 合并后的 API 契约与兼容性是否成立，重点覆盖：

1. `generate` 与 `stream done` 是否都返回统一 `story_memory`
2. `story_memory.operation.operation_id` 是否可从当前轮事件稳定推导
3. 会话级统一读模型 `GET /api/v2/story/session/{session_id}/story-memory` 是否可用
4. 兼容字段是否保留（`summary_memory_snapshot / entity_state_snapshot / entity_state_updates / world_update` 等）
5. 旧兼容桥接接口是否仍可读取（`/story/session/{session_id}/entity-state`）

## 2. 执行信息

- 执行日期：2026-04-10
- 最近一次执行时间：`2026-04-10 18:19:46`
- 目标服务：`http://127.0.0.1:8000`
- 验证脚本：`story_rag_service/scripts/smoke_story_memory_plan_20260410.py`
- Provider：`deepseek`
- Model：`deepseek-chat`
- 结果明细：`story_rag_service/docs/TestResult/Plan0410_StoryMemoryMerge_Validation_Run.json`

## 3. 总体结果

- 总检查项：`25`
- 通过：`25`
- 失败：`0`
- 总体状态：`全部通过`

## 4. 关键验收项结果

### 4.1 generate / stream done 返回 story_memory

1. `generate_returns_story_memory`：通过（200）
2. `stream_done_returns_story_memory`：通过（200）
3. 两条链路均包含完整五个视图：
   - `operation`
   - `semantic`
   - `runtime`
   - `entity`
   - `timeline`

### 4.2 operation_id 可稳定推导

1. `generate_story_memory_operation_derivable`：通过
   - operation_id: `generate:bcde8c11-64c8-4dbc-8c2f-0c1cd70b4a99`
2. `stream_story_memory_operation_derivable`：通过
   - operation_id: `generate:c7d7f9ef-f230-420c-aa30-4669d5cc0dbd`
3. `regenerate_story_memory_operation_derivable`：通过
   - operation_id: `regenerate:5b1792af-82ce-4171-8b06-96f3a2e7f9f3`
4. `session_story_memory_operation_derivable`：通过
   - session snapshot operation_id: `regenerate:5b1792af-82ce-4171-8b06-96f3a2e7f9f3`

结论：`story_memory.operation.operation_id` 能与当轮 `memory_updates` 事件链对齐，满足“可稳定推导”的验收目标。

### 4.3 会话级统一读模型与分页契约

1. `session_story_memory_snapshot_available`：通过（200）
2. `session_story_memory_timeline_shape_valid`：通过
   - timeline_total: `13`
   - timeline_event_count(page=1,page_size=50): `13`
3. `story_memory_pagination_page_size_effective`：通过
   - page_size=1 时 timeline_event_count<=1
4. `story_memory_pagination_limit_enforced`：通过
   - page_size=201 返回 422（符合 `le=200` 约束）
5. `story_memory_snapshot_404_for_unknown_session`：通过
   - 未知 session 返回 404

### 4.4 兼容字段与桥接接口

1. `generate_compat_fields_preserved`：通过
2. `stream_done_compat_fields_preserved`：通过
3. `regenerate_compat_fields_preserved`：通过
4. `entity_state_bridge_api_readable`：通过（200）

结论：旧字段兼容层和旧桥接读取路径仍可用，未因 Story Memory 合并产生破坏性回归。

## 5. 结论

本次 04-10 Story Memory 合并 smoke 验证在当前本地环境下全量通过（25/25）。

从 API 契约层面看：

1. 统一 `story_memory` 已稳定落在 generate / stream done / regenerate / session snapshot 链路。
2. operation 维度在后端可回溯、可推导、可对齐。
3. 会话级 `story-memory` 聚合读模型与分页边界行为符合设计预期。
4. 兼容字段和旧桥接接口仍正常，满足迁移期“兼容不破坏”要求。
