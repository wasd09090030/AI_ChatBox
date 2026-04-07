# 记忆更新事件契约与一致性 Smoke API 验证报告（2026-03-27）

## 1. 目标与依据

本次验证依据：
- `story_rag_service/docs/Plan/Plan_2026-03-27_记忆更新事件契约与一致性可视化实施方案.md`

验证目标：
1. 验证 `memory_updates` 在关键链路中可用且结构稳定。
2. 验证 rollback / regenerate / adjustment commit 后，SQLite 真相源与派生状态至少可解释。
3. 验证 `memory_update_journal` 与 API 返回事件的一致性。

---

## 2. 执行环境

- OS: Windows 11（PowerShell）
- 服务地址: `http://127.0.0.1:8012`
- 用户: `user_1773820783085_bk1gzshza`
- Provider / Model: `deepseek` / `deepseek-chat`
- 数据库: `story_rag_service/data/chatbox.db`

---

## 3. Smoke 设计

### 3.1 前置可用性

1. `GET /api/v2/health`
2. `GET /api/v2/providers`（带 `X-User-ID`）
3. `POST /api/v2/providers/test-connection`

### 3.2 memory_updates 契约链路

1. `POST /api/v2/story/session`
2. 连续两轮 `POST /api/v2/story/generate`
3. `DELETE /api/v2/story/session/{session_id}/messages/last`
4. `POST /api/v2/story/session/{session_id}/regenerate`

验证点：
- API 返回 `memory_updates`
- 动作语义符合场景：`updated / rebuilt / reindexed`
- `story_session_messages` 数量变化符合预期
- `memory_update_journal` 记录与返回动作一致

### 3.3 story adjustment commit 一致性链路

1. `POST /api/v2/worlds`
2. `POST /api/v2/stories`
3. `POST /api/v2/stories/{story_id}/segments`
4. `POST /api/v2/story/adjustments/polish`
5. `POST /api/v2/stories/{story_id}/adjustments/commit`
6. `GET /api/v2/stories/{story_id}`

验证点：
- polish 不直接改正文（草稿态）
- commit 后正文落库
- commit 返回 `memory_updates` 至少含 `episodic:rebuilt` 与 `episodic:reindexed`
- commit session 的 `story_session_messages` 与 journal 记录可见

---

## 4. 执行结果

执行汇总：`20/20` 通过。

| 步骤 | 预期 | 实际 | 结论 |
| --- | --- | --- | --- |
| health | healthy | 200 + `healthy` | 通过 |
| providers_ready | deepseek 可用 | `available=true` | 通过 |
| provider_connection | 连通成功 | `success=true`, `latency_ms=1301` | 通过 |
| session_create | 创建会话 | `session_id=mem-contract-1774620412-aeabc0` | 通过 |
| generate_round1_memory_updates | 返回 memory_updates | `episodic:updated:generate` | 通过 |
| db_after_gen1_messages | 消息入库 | message_count=2 | 通过 |
| generate_round2_memory_updates | 返回 memory_updates | `episodic:updated:generate` | 通过 |
| db_after_gen2_messages | 消息增长 | message_count=4 | 通过 |
| rollback_memory_contract | 返回 rollback 事件 | `rebuilt + reindexed` | 通过 |
| db_after_rollback_message_delta | 删除一条消息 | 4 -> 3 | 通过 |
| regenerate_memory_contract | 返回 regenerate 事件 | `rebuilt + reindexed + updated` | 通过 |
| db_after_regenerate_message_growth | 消息恢复增长 | 3 -> 4 | 通过 |
| world_create | 创建世界 | `world_id=3ef0ec4b-0304-42fd-b073-45b7557a2226` | 通过 |
| story_create | 创建故事 | `story_id=627b8499-539d-4ade-b59b-28256a05d64e` | 通过 |
| story_add_segment | 新增段落 | `segment_id=0fd49f17-167c-424c-9621-6f291ca2ffbe` | 通过 |
| adjustment_polish | 返回润色文本 | `锈迹斑斑的铜钥匙` | 通过 |
| adjustment_draft_only | commit 前正文不变 | 仍为 `陈旧的铜钥匙` | 通过 |
| adjustment_commit_memory_contract | commit 触发重建事件 | `rebuilt + reindexed`，`rebuild_history_reindexed=true` | 通过 |
| adjustment_commit_persisted | commit 后正文变更落库 | 文本更新为 `锈迹斑斑的铜钥匙` | 通过 |
| commit_session_db_messages | commit session 消息可见 | message_count=2 | 通过 |

---

## 5. 关键证据

- 会话：`mem-contract-1774620412-aeabc0`
- commit 会话：`commit-mem-contract-1774620412-aeabc0`
- 世界：`3ef0ec4b-0304-42fd-b073-45b7557a2226`
- 故事：`627b8499-539d-4ade-b59b-28256a05d64e`
- 段落：`0fd49f17-167c-424c-9621-6f291ca2ffbe`

API 返回关键动作：
- generate: `episodic:updated:generate`
- rollback: `episodic:rebuilt:rollback`, `episodic:reindexed:rollback`
- regenerate: `episodic:rebuilt:regenerate`, `episodic:reindexed:regenerate`, `episodic:updated:generate`
- adjustment commit: `episodic:rebuilt:story_adjustment_commit`, `episodic:reindexed:story_adjustment_commit`

SQLite 核验（`memory_update_journal`）：
- 与 API 返回的动作/来源一致
- rollback 与 regenerate 均形成可追踪事件链
- commit 会话可见重建事件，且 `story_session_messages` 已重建

---

## 6. 与 03-27 计划的对齐结论

已验证通过：
1. `memory_updates` 已成为可消费契约（generate / rollback / regenerate / commit 均可见）。
2. rollback / regenerate 不再只有“删消息”，而是有显式重建与索引事件。
3. story adjustment commit 已输出重建类事件，并可通过 DB journal 回溯。

当前观察到的差距（非失败，属于覆盖边界）：
1. 本轮会话中 `conversation_summaries` 未形成有效记录，故未触发 `semantic:reset` 或 `semantic:marked_stale` 事件。
2. 若要严格覆盖计划中的 semantic 分层契约，需要补一组“先产生 summary，再 rollback/regenerate”的定向 smoke。

---

## 7. 结论

本轮 smoke 结论：
- 2026-03-27 计划的“事件契约可见性 + 一致性可解释性”核心目标已在 API 与 SQLite 层得到验证。
- 当前链路已具备前端接入 `memory_updates` 的基础稳定性。
- 后续建议追加一个 semantic 定向场景，专门覆盖 `summary stale/reset` 事件，补齐分层契约验收闭环。
