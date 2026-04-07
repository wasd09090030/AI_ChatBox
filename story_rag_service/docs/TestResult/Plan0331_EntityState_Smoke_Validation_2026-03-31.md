# Plan 2026-03-31 实体状态追踪验证报告（2026-03-31）

## 1. 验证范围

本轮根据 Plan_2026-03-31 文档，执行动态 smoke 验证，覆盖：

1. 普通生成（`/api/v2/story/generate`）
2. 流式生成（`/api/v2/story/generate/stream` done 事件）
3. rollback（`DELETE /api/v2/story/session/{session_id}/messages/last`）
4. regenerate（`POST /api/v2/story/session/{session_id}/regenerate`）
5. story adjustment commit（`POST /api/v2/stories/{story_id}/adjustments/commit`）
6. story segment rollback（`DELETE /api/v2/stories/{story_id}/segments/last`）
7. 实体状态读/重建接口（story 与 session 两个维度）
8. `memory_update_journal` 会话时间线中的 `entity_state` 事件
9. 服务重启后的持久化可读性（恢复场景）

## 2. 执行方式

执行脚本：

- `story_rag_service/scripts/smoke_entity_state_plan_20260331.py`

执行命令：

- `SMOKE_BASE_URL=http://127.0.0.1:8000`
- `python scripts/smoke_entity_state_plan_20260331.py`

结果产物：

- `story_rag_service/docs/TestResult/Plan0331_EntityState_Validation_Run.json`

执行时间：

- 2026-03-31 17:44:09（UTC+8）

## 3. 总体结果

- 总检查项：34
- 通过：18
- 失败：16
- 结论：`all_passed = false`

关键对象：

- world_id: `4be20e1a-d562-4e82-92d1-435f847eeb93`
- story_id: `d06c4d7c-d28c-4358-8909-257e0c64c1de`
- session_id: `story-d06c4d7c-d28c-4358-8909-257e0c64c1de-v2`

## 4. 关键阻塞问题（P0）

### 4.1 实体状态重建核心异常：`KeyError: '0,18'`

服务端日志显示，实体状态重建在正则模板格式化阶段抛出异常：

- 触发点：`services/entity_state_manager.py` -> `_extract_inventory_changes(...)`
- 语句：`pattern.format(name=escaped_name)`
- 异常：`KeyError: '0,18'`

根因是正则模板中使用了 `{0,18}` 量词，同时又调用了 `.format(...)`，导致量词被当作格式化占位符。

因此，以下路径都无法产出有效实体状态：

1. generate 后在线重建
2. stream done 后在线重建
3. rollback reconcile 重建
4. regenerate reconcile + 生成后重建
5. story adjustment commit 重建
6. story segment rollback 重建
7. story/session rebuild API

### 4.2 失败表现（与 Plan 验收项直接冲突）

1. `entity_state_snapshot` 在 generate/stream/regenerate 中为空
2. `GET /stories/{story_id}/entity-state` 与 `GET /story/session/{session_id}/entity-state` 返回 `total = 0`
3. `POST /stories/{story_id}/entity-state/rebuild` 与 `POST /story/session/{session_id}/entity-state/rebuild` 触发 500
4. `memory_updates` 中虽有 `memory_layer = entity_state`，但均为 `status = failed`

## 5. 失败项清单

本轮失败检查项如下：

1. generate_response_entity_snapshot
2. generate_memory_updates_contains_entity_state
3. generate_operation_chain_aligned
4. session_entity_state_read
5. story_entity_state_read
6. timeline_contains_generate_entity_events
7. stream_done_contains_entity_snapshot
8. stream_state_transition_applied
9. regenerate_response_entity_snapshot
10. session_entity_rebuild_api
11. story_adjustment_commit_rebuild_entity
12. story_entity_state_after_commit
13. story_segment_rollback_rebuild_entity
14. story_entity_state_after_segment_rollback
15. story_entity_rebuild_api
16. timeline_contains_entity_sources

## 6. 服务重启恢复验证（补充）

在上述 smoke 后，执行了一次服务重启并对同一 session 复查：

重启前：

- entity-state total = 0
- entity_state 事件数 = 4
- failed entity_state 事件数 = 4

重启后：

- entity-state total = 0
- entity_state 事件数 = 4
- failed entity_state 事件数 = 4

结论：

1. 持久化与恢复链路可读（数据未丢失）
2. 但恢复的是“失败结果”，不代表实体状态功能可用

## 7. 结论

按照 Plan_2026-03-31 的核心验收目标（生成后可见实体态、回滚/重生/提交后可重建、可读取当前实体状态），本轮验证结论为：

1. **未通过**
2. 存在单点 P0 阻塞缺陷（实体重建正则模板格式化异常）
3. 在修复该缺陷前，前端实体态势板与相关时间线只能看到失败事件，无法获得有效实体快照

## 8. 修复建议（最小改动）

在 `services/entity_state_manager.py` 中，将用于 `.format(name=...)` 的正则模板量词花括号转义为双花括号（例如 `{0,18}` -> `{{0,18}}`），并对同类模板做一次全量检查（库存增减与目标提取模板）。修复后建议复跑本 smoke 脚本并更新本报告。