# Plan 2026-03-28 双模式故事创作测试验证（阶段推进 + Prompt重点）

## 1. 测试目标

基于 Plan_2026-03-28_双模式故事创作技术设计方案，验证两项核心能力：

1. 阶段推进是否有效：`scripted` 模式下，`hold/advance/complete` 是否按预期影响 `runtime_state_snapshot`。
2. Prompt 调整输出重点是否有效：同一阶段同一事件下，通过不同 `focus_instruction` 是否能显著改变输出重心。

同时补充双模式分流验证：`scripted` 与 `improv` 返回形态差异是否符合设计预期。

## 2. 本轮测试剧本（完整 4 阶段）

剧本标题：雾港潮线账本（四幕）

1. 第一幕：雨夜入港
- 事件：拾得潮线账本
- 目标：确认账本记录与失踪案有关

2. 第二幕：账本解码
- 事件：解码账本页码
- 目标：解析潮汐密码并锁定灯塔地下仓库

3. 第三幕：灯塔对峙
- 事件：灯塔仓库对峙
- 目标：阻止证据焚毁并保住关键账页

4. 第四幕：破晓收束
- 事件：黎明公证
- 目标：公开真相并承担代价，完成主线收束

伏笔：潮线缺页（第一幕埋设，第四幕回收）

## 3. 执行方式

自动化脚本：
- `story_rag_service/scripts/smoke_dual_mode_plan_20260328.py`

产物 JSON：
- `story_rag_service/docs/TestResult/Plan0328_DualMode_Validation_Run.json`

执行时间：2026-03-28 21:05:07（UTC+8）

## 4. 测试结果总览

- 总检查项：16
- 通过：16
- 失败：0
- 结论：`all_passed = true`

关键运行上下文（本次通过轮次）：
- world_id: `ed03b561-2b55-40b3-a3ac-e30f737dc210`
- story_id: `36589286-3424-48fe-b685-8e7bb8856e23`
- script_design_id: `bd8acb82-a5ff-4dc2-901f-25ed8a9d56bc`
- session_id: `story-36589286-3424-48fe-b685-8e7bb8856e23-v2`

## 5. 阶段推进有效性验证

### 5.1 scripted + hold（第一幕）

- 断言：`current_event_id` 保持在第一幕事件，不自动推进。
- 实测：通过。
- 证据：`consistency_check.notes` 返回“本轮仅描写，不自动推进剧情状态”。

### 5.2 scripted + complete（第一幕 -> 第二幕）

- 断言：完成第一幕事件后推进到第二幕事件。
- 实测：通过。
- 证据：
  - `current_event_id`: `event-2-78edfd56`
  - `completed_event_ids` 包含 `event-1-17dbccdb`

### 5.3 scripted + complete（第二幕 -> 第三幕）

- 断言：完成第二幕事件后推进到第三幕事件。
- 实测：通过。
- 证据：
  - `current_event_id`: `event-3-02a52252`
  - `completed_event_ids` 包含 `event-2-78edfd56`

### 5.4 scripted + advance（第三幕）

- 断言：`advance` 不应直接把当前事件标记完成。
- 实测：通过。
- 证据：
  - `current_event_id` 仍为 `event-3-02a52252`
  - `completed_event_ids` 不包含 `event-3-02a52252`

### 5.5 scripted + complete（第三幕 -> 第四幕 -> 终幕完成）

- 断言：
  1. 第三幕 complete 后进入第四幕事件。
  2. 第四幕 complete 后停留终幕，并记录该事件完成。
- 实测：通过。
- 证据：
  - 第三幕 complete 后：`current_event_id = event-4-6488d3e0`
  - 第四幕 complete 后：`current_event_id` 仍为 `event-4-6488d3e0`
  - `completed_event_ids` 包含 `event-4-6488d3e0`

结论：阶段推进机制有效，且 `hold/advance/complete` 语义分离符合 Plan 预期。

## 6. Prompt 调整输出重点有效性验证

测试场景：第二幕“解码账本页码”，同阶段同事件分别注入两组 focus。

- Focus A（环境压迫）：钟声/座钟/潮湿/海盐/铁锈/回声/空廊
- Focus B（解码逻辑）：密码/密文/页码/符号/译码/坐标/重排

脚本采用“同义词感知 + 交叉差异”判定：

- `score_a_on_a > score_a_on_b`
- `score_b_on_b > score_b_on_a`

本轮实测分值：

- `score_a_on_a = 3`
- `score_b_on_a = 1`
- `score_a_on_b = 0`
- `score_b_on_b = 2`

判定：通过。

说明：
- Focus A 输出文本显著出现“潮湿、铁锈、座钟”等环境压迫线索。
- Focus B 输出文本显著出现“密码/符号/坐标/解码步骤”等技术解码线索。

结论：Prompt 微调可有效改变同阶段输出重心，符合 Plan 中“prompt 负责本轮重点微调而非主线调度”的设计目标。

## 7. 双模式分流验证

- 用例：同会话下发起 `creation_mode=improv` 请求。
- 断言：返回 `creation_mode=improv` 且 `consistency_check = null`（不走严格一致性合同）。
- 实测：通过。

结论：双模式执行分流有效。

## 8. 综合结论

本轮验证结果表明：

1. 双模式主干有效：`scripted` 与 `improv` 分流行为符合设计。
2. 严格模式推进有效：4 阶段完整剧本可按 `hold/advance/complete` 进行稳定推进。
3. Prompt 调整有效：在同阶段下可以显著改变模型输出重点，但不替代结构化推进真相源。

因此，Plan 中“阶段推进可控 + prompt微调可用”的核心验收目标在本轮 smoke 中通过。
