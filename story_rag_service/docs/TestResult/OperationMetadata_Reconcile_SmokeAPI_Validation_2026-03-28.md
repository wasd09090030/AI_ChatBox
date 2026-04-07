# operation 元数据联调 Smoke 验证报告（2026-03-28）

## 1. 目标

基于二期计划，执行一轮完整联调链路并验证：

1. `generate -> rollback -> regenerate -> story_adjustment_commit` 每一步的 API 返回中，`operation_id / sequence / display_kind` 字段完整且可解释。
2. `memory_update_journal` 中同一 `operation_id` 的记录与 API 返回逐项对账一致。
3. 数据库已迁移至最新 revision，包含 operation 元数据字段。

---

## 2. 迁移执行结果

按要求执行：

1. `python -m alembic upgrade head` 初次执行失败：`users already exists`。
2. 原因排查：数据库为已初始化状态，`alembic_version` 表存在但为空（`count=0`）。
3. 处理动作：
   - `python -m alembic stamp head`
   - `python -m alembic upgrade head`
4. 最终结果：迁移元数据与当前库结构已对齐到 `20260328_0006`，后续升级命令正常返回。

说明：
- 本次未清库、未重建业务表，仅修正迁移版本标记。

---

## 3. 联调链路与断言

执行链路：

1. `POST /api/v2/story/generate`
2. `DELETE /api/v2/story/session/{session_id}/messages/last`
3. `POST /api/v2/story/session/{session_id}/regenerate`
4. `POST /api/v2/stories/{story_id}/adjustments/commit`

每一步统一断言：

1. API `memory_updates` 非空。
2. 同一步骤内事件 `operation_id` 唯一且非空。
3. `sequence` 为正整数且递增。
4. `display_kind` 非空。
5. 以 `operation_id + session_id` 查询 journal 后，与 API 事件逐项一致：
   - operation_id
   - sequence
   - display_kind
   - memory_layer
   - action
   - source
   - status

---

## 4. 执行结果

本轮总计 17 项检查，`17/17` 通过。

- session_id: `opmeta-1774678963-b6a47e`
- generate.operation_id: `generate:7fc5ac0b-cf78-46e5-9d95-81cf139033c1`
- rollback.operation_id: `rollback:9f56030b-170d-44a2-bc03-6ea5fb1394d9`
- regenerate.operation_id: `regenerate:a49dd918-b15c-4973-acdb-c2028c927544`
- commit.operation_id: `story_adjustment_commit:ec356b63-d7c7-4141-a5de-12075dafc5c4`

关键检查结果：

1. `journal_columns`：通过
   - `memory_update_journal` 已包含 `operation_id`、`sequence`、`display_kind`。
2. `generate_operation_contract`：通过
3. `generate_api_journal_reconcile`：通过
4. `rollback_operation_contract`：通过
5. `rollback_api_journal_reconcile`：通过
6. `regenerate_operation_contract`：通过
7. `regenerate_api_journal_reconcile`：通过
8. `commit_operation_contract`：通过
9. `commit_api_journal_reconcile`：通过

---

## 5. 实际返回样例（节选）

### generate

- API 事件：
  - `operation_id=generate:...`
  - `sequence=1`
  - `display_kind=write`
  - `memory_layer=episodic`
  - `action=updated`

- Journal 对账：完全一致。

### rollback

- API 事件序列：
  1. `sequence=1`, `display_kind=session_rebuild`, `episodic:rebuilt:rollback`
  2. `sequence=2`, `display_kind=index_rebuild`, `episodic:reindexed:rollback`

- Journal 对账：完全一致。

### regenerate

- API 事件序列：
  1. `sequence=1`, `display_kind=session_rebuild`, `episodic:rebuilt:regenerate`
  2. `sequence=2`, `display_kind=index_rebuild`, `episodic:reindexed:regenerate`
  3. `sequence=3`, `display_kind=write`, `episodic:updated:generate`

- Journal 对账：完全一致。

### story_adjustment_commit

- API 事件序列：
  1. `sequence=1`, `display_kind=session_rebuild`, `episodic:rebuilt:story_adjustment_commit`
  2. `sequence=2`, `display_kind=index_rebuild`, `episodic:reindexed:story_adjustment_commit`

- 说明：本轮按“单次 generate 后立即 commit”执行，未先累积出 summary，因此该 operation 未出现 `semantic:reset:*` 事件。

- Journal 对账：完全一致。

---

## 6. 结论

本轮联调 smoke 结论：

1. `operation_id / sequence / display_kind` 在四条核心链路均有稳定返回。
2. Journal 中同 operation 事件链与 API 返回可逐项对账，无偏差。
3. 二期计划中“operation 分组与可解释展示”的关键数据前提已满足。

本结果可直接作为后续前端管理区 operation 分组展示的后端契约依据。
