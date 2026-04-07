# Plan 2026-03-28（更新版）双模式验证报告（2026-03-29）

## 1. 验证范围

本轮基于已更新的 Plan 文档，执行动态 smoke 验证，覆盖以下重点：

1. 双模式主干：scripted / improv 分流。
2. 严格模式阶段推进：hold / advance / complete 语义是否生效。
3. Prompt 微调重点：同阶段双 focus 是否可稳定拉开输出重心。
4. 新增撤销链路：
- 回滚时会话消息删除是否生效。
- story 持久化 segment 是否同步删除。
- runtime 是否按“上一段快照 / 初始快照”恢复。

## 2. 执行方式

执行脚本：
- story_rag_service/scripts/smoke_dual_mode_plan_20260328.py

执行命令（本轮）：
- SMOKE_BASE_URL=http://127.0.0.1:8000

结果产物 JSON：
- story_rag_service/docs/TestResult/Plan0328_DualMode_Validation_Run.json

执行时间：
- 2026-03-29 22:20:22（UTC+8）

## 3. 总体结果

- 总检查项：22
- 通过：22
- 失败：0
- 结论：all_passed = true

关键对象：
- world_id: 6b001a9f-385e-40a3-8aa5-a06e76b9c268
- story_id: ff55ccc7-ddb2-49de-a8df-5de2217a73ea
- session_id: story-ff55ccc7-ddb2-49de-a8df-5de2217a73ea-v2
- script_design_id: 2fd8821c-67c4-49c3-8a4e-e513c78a22d0

## 4. 与更新 Plan 对齐的验证结论

### 4.1 严格模式推进控制

通过：
1. scripted + hold：不推进当前事件。
2. scripted + advance：不自动标记完成。
3. scripted + complete：按阶段推进并累计 completed_event_ids。

结论：推进意图控制符合更新 Plan 预期。

### 4.2 Prompt 微调重点有效性

本轮采用强化约束（A 禁技术术语、B 减环境描写）后结果稳定通过：

- score_a_on_a = 2
- score_b_on_a = 0
- score_a_on_b = 0
- score_b_on_b = 5

结论：同阶段下可通过 focus_instruction 有效改变输出重心。

### 4.3 新增“严格模式撤销链路”验证（本轮新增）

本轮新增并通过以下断言：

1. set_runtime_initial_snapshot：成功写入 runtime_initial_snapshot。
2. seed_segments_for_rollback：成功种入 2 个带 runtime_state_snapshot 的 segment。
3. session_rollback_step1：会话回滚 API 成功。
4. strict_rollback_restore_previous_runtime：
- segment 数量 2 -> 1
- runtime 恢复到上一段快照对应事件（event-4-27bb5d07）。
5. session_rollback_step2：会话再次回滚成功。
6. strict_rollback_restore_initial_runtime：
- segment 数量 1 -> 0
- runtime 恢复到初始快照事件（event-1-a988addc）。

回滚证据摘要：
- segments_before = 2
- segments_after_first_rollback = 1
- segments_after_second_rollback = 0
- restored_event_after_first_rollback = event-4-27bb5d07
- restored_event_after_second_rollback = event-1-a988addc

结论：更新 Plan 中“撤销时 segment 与 runtime 同步回退”的关键链路已通过动态验证。

## 5. 双模式分流结果

通过：
- improv 请求返回 creation_mode = improv
- consistency_check = null

结论：strict / improv 分流行为正确。

## 6. 说明与边界

本轮为后端 API 动态验证，重点验证执行语义与数据一致性。

未在本轮自动化覆盖的内容：
1. 严格模式页面中的 UI 交互细节（如顶部抽屉文案、手风琴折叠样式）
2. 前端端到端视觉行为与控件可用性

上述项建议补充一次前端手工回归或 E2E 自动化验证。

## 7. 最终结论

针对已更新 Plan，本轮 smoke 结果显示：

1. 双模式主干可用。
2. 严格模式阶段推进可控。
3. Prompt 微调可有效改变输出重点。
4. 更新新增的严格模式撤销链路（segment 删除 + runtime 恢复）已验证通过。

因此，更新版 Plan 的核心可执行验收项在本轮验证中通过。
