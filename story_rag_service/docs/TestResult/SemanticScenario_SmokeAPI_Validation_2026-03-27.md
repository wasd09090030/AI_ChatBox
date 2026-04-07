# Semantic 场景 Smoke API 验证报告（2026-03-27）

## 1. 验证目标

按需求执行并观察以下链路：

1. 先生成足够轮次，使 `conversation_summaries` 确实产生记录。
2. 执行 rollback。
3. 执行 regenerate。
4. 执行 story adjustment commit。

重点关注：
- `memory_updates` 中是否出现语义事件（`semantic:created` / `semantic:reset`）。
- `conversation_summaries` 在关键步骤后是否与事件语义一致。
- `memory_update_journal` 是否留痕并与 API 返回一致。

---

## 2. 执行环境

- OS: Windows 11（PowerShell）
- Base URL: `http://127.0.0.1:8012`
- User: `user_1773820783085_bk1gzshza`
- Provider/Model: `deepseek` / `deepseek-chat`
- DB: `story_rag_service/data/chatbox.db`

---

## 3. 执行结果总览

本轮共 14 项检查，`14/14` 通过。

- session_id: `semantic-focus-1774621335-c6abf9`
- world_id: `a7a12aff-baa9-4078-81fd-82593dcd4e68`
- story_id: `1460f3d1-f2b8-4d2d-b217-b8fe427e3fab`
- segment_id: `ed17dac4-414f-4d2f-9d09-b12e0e08626c`

---

## 4. 分步骤观察

### 4.1 先生成到 summary 落库

- 前 1~3 轮：仅出现 `episodic:updated:generate`。
- 第 4 轮：出现 `semantic:created:generate`。
- 数据库确认：`conversation_summaries` 已有有效记录（`exists=true`）。

结论：
- “先产出 summary 再做后续动作”的前置条件已满足。

### 4.2 rollback

请求：`DELETE /api/v2/story/session/{session_id}/messages/last`

返回事件：
- `episodic:rebuilt:rollback`
- `episodic:reindexed:rollback`
- `semantic:reset:rollback`

数据库：
- 消息数 `8 -> 7`
- `conversation_summaries` 记录被移除（`exists=false`）

结论：
- rollback 已触发语义重置，且 DB 状态与事件一致。

### 4.3 regenerate

请求：`POST /api/v2/story/session/{session_id}/regenerate`

返回事件：
- `episodic:rebuilt:regenerate`
- `episodic:reindexed:regenerate`
- `episodic:updated:generate`
- `semantic:created:generate`

数据库：
- 消息数恢复到 `8`
- `conversation_summaries` 再次存在（`exists=true`）

结论：
- regenerate 后语义层成功“再物化”，一致性恢复正常。

### 4.4 story adjustment commit

对同一 `session_id` 执行：
- polish（仅草稿）
- commit（正式提交）

commit 返回事件：
- `episodic:rebuilt:story_adjustment_commit`
- `semantic:reset:story_adjustment_commit`
- `episodic:reindexed:story_adjustment_commit`

响应标志：
- `rebuild_summary_reset=true`
- `rebuild_history_reindexed=true`

数据库：
- `conversation_summaries` 再次移除（`exists=false`）

结论：
- adjustment commit 在语义层触发 reset，行为符合预期。

---

## 5. Journal 对账

`memory_update_journal`（同 session 最近事件）与 API 返回一致，关键序列如下：

1. `semantic:created:generate`
2. `semantic:reset:rollback`
3. `semantic:created:generate`（regenerate 后）
4. `semantic:reset:story_adjustment_commit`

说明：
- 语义事件在“生成→回滚→重生→提交”完整链路中可追踪、可解释。

---

## 6. 结论（查看效果）

这组 semantic 场景效果良好，核心行为全部符合预期：

1. 可稳定把 summary 从无到有（`semantic:created`）。
2. rollback 会显式 reset 并移除 summary（`semantic:reset:rollback`）。
3. regenerate 可在同会话重新创建 summary（`semantic:created:generate`）。
4. story adjustment commit 会再次 reset summary（`semantic:reset:story_adjustment_commit`），并同步完成 history 重建。

整体上，`memory_updates + conversation_summaries + memory_update_journal` 三者在本链路表现出一致且可审计的语义行为。
