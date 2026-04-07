# Plan 2026-03-31 实体状态追踪修复后复测报告（2026-03-31）

## 1. 复测目标

基于同一脚本与同一场景，复跑 03-31 实体状态 smoke，验证修复后是否恢复以下能力：

1. generate / stream 返回可用 `entity_state_snapshot`
2. rollback / regenerate / story adjustment commit / story segment rollback 的实体状态重建可用
3. story/session 两类 entity-state rebuild API 可用
4. `memory_update_journal` 中 entity_state 事件链路可追踪

## 2. 执行信息

执行脚本：

- `story_rag_service/scripts/smoke_entity_state_plan_20260331.py`

执行时间：

- 2026-03-31 18:10:49（UTC+8）

结果产物：

- `story_rag_service/docs/TestResult/Plan0331_EntityState_Validation_Run.json`

本轮关键对象：

- world_id: `49cfe3d8-696e-405b-8577-952dfc0ed759`
- story_id: `8821e0e5-235d-4e51-b57d-02cef7b60113`
- session_id: `story-8821e0e5-235d-4e51-b57d-02cef7b60113-v2`

## 3. 总体结果

- 总检查项：34
- 通过：33
- 失败：1
- 结论：`all_passed = false`

与上一轮（18/34）相比，核心实体状态链路已明显恢复。

## 4. 通过项摘要（核心链路）

以下关键能力均已通过：

1. generate 返回实体快照（`generate_response_entity_snapshot`）
2. generate 的 `memory_updates` 已包含 `memory_layer=entity_state`
3. session/story 当前实体状态读取可用（`total=2`，可读到张三/李四）
4. stream done payload 含实体快照，且地点/物品变更可观察
5. rollback 后实体状态重建可见
6. regenerate 返回实体快照，且包含 entity_state 事件
7. session rebuild API 通过（`rebuilt=true`, `entity_count=2`）
8. story adjustment commit 重建通过（`rebuild_entity_state_rebuilt=true`）
9. story segment rollback 重建通过（`rebuild_entity_state_rebuilt=true`）
10. story rebuild API 通过（`rebuilt=true`, `entity_count=2`）
11. timeline 维度可看到 generate / rollback / regenerate / commit / rollback / 两类 rebuild API 来源

## 5. 唯一未通过项

失败检查项：

1. `generate_operation_chain_aligned`

失败细节：

- episodic_operation_ids: `generate:07a10319-69e1-46a4-9131-105469cafc89`
- entity_operation_ids: `generate:97dbfa30-cde8-4e9e-b819-373886ddde88`
- shared_operation_ids: `[]`

说明：

- 本轮生成中，episodic 与 entity_state 事件仍使用了不同 `operation_id`。
- 这与 Plan 中“同轮操作共用 operation_id / sequence 链路以便对账”的目标仍有差距。

## 6. 结论

修复后，03-31 Plan 的大部分功能性验收目标已恢复并可运行（33/34）。
当前剩余问题已收敛为单一一致性项：**同轮生成的 operation_id 对齐**。

若将 `generate_operation_chain_aligned` 修复为通过，本 smoke 将达到全量通过状态。