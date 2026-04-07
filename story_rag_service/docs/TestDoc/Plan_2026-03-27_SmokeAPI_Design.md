# Plan_2026-03-27 对应 Smoke API 验证设计

## 1. 设计目标

本设计用于验证以下三类目标是否达成：

1. memory_updates 事件契约稳定可用。
2. rollback / regenerate / story adjustment commit 的一致性治理可解释。
3. semantic 层（conversation_summaries）在关键动作前后与事件语义一致。

本设计只定义测试方案，不绑定具体实现脚本。

---

## 2. 测试范围

### 2.1 接口范围

- GET /api/v2/health
- GET /api/v2/providers
- POST /api/v2/providers/test-connection
- POST /api/v2/story/session
- POST /api/v2/story/generate
- DELETE /api/v2/story/session/{session_id}/messages/last
- POST /api/v2/story/session/{session_id}/regenerate
- POST /api/v2/worlds
- POST /api/v2/stories
- POST /api/v2/stories/{story_id}/segments
- POST /api/v2/story/adjustments/polish
- POST /api/v2/stories/{story_id}/adjustments/commit
- GET /api/v2/stories/{story_id}

### 2.2 数据范围

- story_sessions
- story_session_messages
- conversation_summaries
- memory_update_journal

---

## 3. 前置条件

1. 服务可启动且 /api/v2/health 返回 healthy。
2. 测试用户已配置可用 provider key。
3. 使用独立 session_id / world_id / story_id，避免污染历史数据。
4. 所有请求使用同一 user_id（X-User-ID）。

---

## 4. 测试剖面

## 4.1 剖面 A：事件契约与一致性基础链路

目标：覆盖 generate、rollback、regenerate、commit 的基础契约。

步骤：
1. health + provider readiness + test-connection。
2. 创建 session。
3. 连续两轮 generate。
4. rollback 一次。
5. regenerate 一次。
6. 创建 world/story/segment。
7. 执行 polish（草稿态）。
8. 执行 adjustment commit。
9. 读取 story 检查正文落库。

核心断言：
- generate 返回 memory_updates，至少含 episodic:updated:generate。
- rollback 返回 episodic:rebuilt:rollback + episodic:reindexed:rollback。
- regenerate 返回 episodic:rebuilt:regenerate + episodic:reindexed:regenerate。
- commit 返回 episodic:rebuilt:story_adjustment_commit + episodic:reindexed:story_adjustment_commit。
- polish 不改正文，commit 才改正文。
- memory_update_journal 与 API 动作序列一致。

通过标准：
- 关键断言全部通过。
- 无 HTTP 5xx。

## 4.2 剖面 B：semantic 深测链路（强制 summary 生成）

目标：专门验证 semantic:created / semantic:reset 行为。

步骤：
1. 创建 session。
2. 循环 generate（最多 N 轮）直到 conversation_summaries 出现记录。
3. rollback 一次。
4. regenerate 一次。
5. 若 regenerate 后 summary 未恢复，补 1~3 轮 generate 直到 summary 恢复。
6. 创建 world/story/segment 并执行 adjustment commit（使用同一 session_id）。

核心断言：
- 生成阶段至少出现 semantic:created:generate。
- rollback 出现 semantic:reset:rollback，且 conversation_summaries 被清理。
- regenerate 后 summary 可再物化（semantic:created:generate）。
- commit 出现 semantic:reset:story_adjustment_commit。
- commit 响应 rebuild_summary_reset=true，rebuild_history_reindexed=true。
- journal 中语义事件序列可回溯（created -> reset -> created -> reset）。

通过标准：
- semantic 事件与 DB 状态逐步一致。
- 无语义漂移（事件说 reset 但 summary 仍存在）。

---

## 5. 断言口径（统一）

### 5.1 API 层

- 状态码：核心路径均为 200。
- 响应字段：
  - memory_updates 为数组且包含 event 字段（layer/action/source/status）。
  - commit 返回 rebuild_summary_reset/rebuild_history_reindexed。

### 5.2 数据层

- story_session_messages：
  - generate 后增长。
  - rollback 后减少。
  - regenerate 后恢复增长。
- conversation_summaries：
  - semantic created 后存在。
  - semantic reset 后不存在。
- memory_update_journal：
  - 会话下动作链与 API 返回一致。

### 5.3 一致性层

同一步骤中，API 事件与 DB 状态必须同时成立。
示例：
- 出现 semantic:reset:rollback 时，conversation_summaries 必须被移除。

---

## 6. SQL 对账建议

建议在每个关键步骤后执行以下查询：

1. 会话消息数：
- SELECT COUNT(*) FROM story_session_messages WHERE session_id=?

2. summary 状态：
- SELECT summary_text, updated_at FROM conversation_summaries WHERE session_id=? ORDER BY updated_at DESC LIMIT 1

3. journal 尾部：
- SELECT memory_layer, action, source, status, committed_at FROM memory_update_journal WHERE session_id=? ORDER BY committed_at DESC LIMIT 20

---

## 7. 失败分类与定位

1. provider_blocked
- 表现：providers 不可用或 test-connection 失败。
- 处理：标记阻断，不进入生成链路。

2. contract_mismatch
- 表现：接口 200 但缺少 memory_updates 或关键字段。
- 处理：判定为契约回归。

3. semantic_drift
- 表现：semantic reset 事件出现，但 summary 未移除；或相反。
- 处理：判定为一致性回归。

4. persistence_drift
- 表现：API 事件存在，journal 无记录或序列错位。
- 处理：判定为落库链路回归。

---

## 8. 推荐执行策略

1. CI/每日：执行剖面 A（快，覆盖契约面）。
2. 发布前：执行剖面 A + B（覆盖 semantic 深测）。
3. 线上灰度回归：优先执行剖面 B，确认语义层无漂移。

---

## 9. 产出要求

每轮 smoke 至少输出：

1. 执行摘要（total/passed/failed）。
2. 关键资源 ID（session_id/world_id/story_id/segment_id）。
3. 关键事件序列（API + journal）。
4. DB 对账快照（messages/summary/journal tail）。
5. 失败归因标签（如有）。

---

## 10. 当前可复用的参考结果

- story_rag_service/docs/TestResult/MemoryEventContract_Consistency_SmokeAPI_Validation_2026-03-27.md
- story_rag_service/docs/TestResult/SemanticScenario_SmokeAPI_Validation_2026-03-27.md

上述两份结果已分别覆盖剖面 A 与剖面 B，可作为后续对比基线。

---

## 11. 统一脚本入口

脚本位置：

- `story_rag_service/scripts/smoke_memory_updates_plan_20260327.py`

运行示例：

1. 仅跑 A：

```powershell
python scripts/smoke_memory_updates_plan_20260327.py --profile A
```

2. 仅跑 B：

```powershell
python scripts/smoke_memory_updates_plan_20260327.py --profile B
```

3. 跑 A+B（默认）：

```powershell
python scripts/smoke_memory_updates_plan_20260327.py --profile all
```

可选输出文件：

```powershell
python scripts/smoke_memory_updates_plan_20260327.py --profile all --output docs/TestResult/Plan0327_Smoke_Run.json
```
