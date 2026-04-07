# Memory Plan Smoke API 验证报告（2026-03-16）

## 1. 目标

验证 `Plan_2026-03-15_记忆架构重构与迁移方案` 已实施后，核心链路是否可用：

- 统一读路径（MemoryOrchestrator / MemoryBundle）
- 统一写路径（MemoryUpdateService）
- 会话与消息生命周期（session create/read/delete/regenerate）
- 生成接口可达性（stream / non-stream）

---

## 2. Smoke API 设计

### 2.1 验证前置

- `GET /api/v2/health`
- 断言：HTTP 200，返回 `status=healthy`

### 2.2 会话生命周期

- `POST /api/v2/story/session`
- `GET /api/v2/story/session/{session_id}`
- `DELETE /api/v2/story/session/{session_id}/messages/last`
- `POST /api/v2/story/session/{session_id}/regenerate`

预期：
- 可创建 session 并返回 `session_id`
- 可读取 metadata
- 删除最后消息在有数据时成功
- regenerate 至少走通参数校验与回滚入口

### 2.3 生成链路

- `POST /api/v2/story/generate`
- `POST /api/v2/story/generate/stream`

预期：
- 非流式返回 `activation_logs` / `summary_memory_snapshot` 等字段
- 流式可返回 SSE 事件，并在 choices 模式下携带 `choices`

---

## 3. 本次执行方法

为避免污染现有运行数据，使用隔离实例执行：

- 端口：`8011`
- 使用临时 Chroma 目录（环境变量 `CHROMA_PERSIST_DIRECTORY` 指向 `data/chroma_db_smoke`）

说明：主实例（默认配置）启动存在 Chroma 初始化失败，见问题 #1。

---

## 4. 执行结果

### 4.1 通过项

- `GET /api/v2/health`：通过（HTTP 200）
- 隔离实例可成功启动并对外提供健康接口

### 4.2 失败项

- `POST /api/v2/story/session`：失败（HTTP 500）
- 导致后续依赖 session 的 smoke 链路全部阻断（generate / regenerate / stream 无法进入有效业务验证）

---

## 5. 问题记录（仅记录，不改代码）

## 问题 #1：默认实例启动阶段失败（Chroma）

现象：
- 服务启动期间报错，应用退出。

关键日志：
- `chromadb.errors.InternalError: error returned from database: (code: 1) table collections already exists`

影响：
- 默认实例无法完成启动，无法进行 API smoke。

判断：
- 属于运行环境/持久化状态问题（向量库目录状态异常或兼容性问题），非本次内存架构 Plan 逻辑直接回归证据。

---

## 问题 #2：session 表缺失导致核心接口 500

现象：
- 隔离实例健康检查通过，但调用 `POST /api/v2/story/session` 返回 500。

关键日志：
- `sqlite3.OperationalError: no such table: story_sessions`

数据库现状（实际列举）：
- 存在：`character_cards`, `conversation_summaries`, `conversations`, `messages`, `story_states`, `users` 等
- 缺失：`story_sessions`, `story_session_messages`

迁移状态对照：
- 代码中存在迁移脚本 `migrations/versions/20260302_0002_story_sessions.py`
- 该脚本定义了 `story_sessions` 与 `story_session_messages` 创建逻辑

影响：
- session 入口不可用，直接阻断 MemoryPlan 的主验证路径（尤其是 episodic/source-of-truth 与 post-generation update）。

判断：
- 高概率为数据库迁移未执行或执行不完整造成。

---

## 6. 结论

本次 smoke 验证结论：

- 目前仅能确认 v2 健康接口可用。
- 由于 `story_sessions` 缺失导致 session API 500，无法完成对 MemoryPlan “读路径+写路径”有效性的端到端验证。
- 需先修复运行前置（Chroma 启动稳定性 + SQLite 迁移完整性）后，才能继续完成完整 smoke。

---

## 7. 建议的下一轮 smoke（待前置修复后）

1. `POST /story/session` 创建新会话。
2. 连续两轮 `POST /story/generate`，校验 `activation_logs` 中 summary/episodic 相关记录。
3. 调用 `DELETE /messages/last` + `POST /regenerate`，检查回滚与重生一致性。
4. 调用 `POST /generate/stream`（`mode=choices`），校验 done 事件中的 `choices` 注入。
5. 重启服务后 `GET /story/session/{id}`，验证会话可恢复（source of truth 为 SQLite）。

---

## 8. 迁移完成后的复测（同日补测）

复测背景：
- 用户确认迁移已完成后，按默认配置（默认模型 deepseek-chat）再次执行 smoke。
- 本次直接使用默认实例启动（不再使用临时 Chroma 目录），服务可正常启动并通过健康检查。

复测链路：
1. `GET /api/v2/health`（通过）
2. `POST /api/v2/story/session`（通过）
3. `GET /api/v2/story/session/{session_id}`（通过）
4. `POST /api/v2/story/generate`（失败）
5. `POST /api/v2/story/generate/stream`（失败）
6. `DELETE /api/v2/story/session/{session_id}/messages/last`（失败，因尚无消息）
7. `POST /api/v2/story/session/{session_id}/regenerate`（失败，因尚无用户消息）

关键返回：
- 生成接口错误：`No API key found for provider 'deepseek' (model: deepseek-chat)`
- Provider 状态接口（现已迁移为 `GET /api/v2/providers`）显示所有 provider `available=false`，包括 deepseek。
- 生成参数契约：`mode=continue` 会触发 422，当前允许值为 `narrative | choices | instruction`。

结论（复测）：
- 迁移问题已修复：`story_sessions` 与 `story_session_messages` 已存在，session 生命周期接口可进入正常路径。
- 当前主阻断不再是数据库迁移，而是默认模型 deepseek 的可用性前置条件未满足（API Key 未配置）。
- 因无法实际调用 LLM，仍无法完成对 MemoryOrchestrator / MemoryUpdateService 的端到端有效性确认。

---

## 9. 改进计划（针对当前不良结果）

目标：
- 把“生成阶段前置条件缺失”从运行时 500 转为可预检、可观测、可快速修复的问题。

### 9.1 短期（当天可执行）

1. 在 smoke 脚本中增加前置检查：
	- 调用 `GET /api/v2/providers`。
	- 若默认 provider（deepseek）不可用，则直接标记 `BLOCKED_BY_PROVIDER_CONFIG` 并输出修复建议，不进入生成链路。

2. 在 smoke 脚本中增加接口契约检查：
	- 对 `/api/v2/story/generate` 的请求体做 schema 预校验，特别是 `mode` 字段。
	- 若出现 422，标记 `BLOCKED_BY_API_CONTRACT`，避免与 provider 问题混淆。

3. 增加连接验证步骤：
	- 调用 `POST /api/v2/providers/test-connection`（provider=deepseek）并记录耗时与错误码。
	- 将错误分类为：`missing_key` / `auth_failed` / `network_unreachable`。

4. 提供 smoke 执行模式：
	- `strict`：必须使用默认 deepseek，失败即阻断。
	- `degraded`：默认 deepseek 不可用时，跳过生成链路，仅验证 session/rollback 合约并输出阻断标签。

### 9.2 中期（1-3 天）

1. 后端增加“生成前可用性短路”：
	- 在 `/story/generate` 入口前先做 provider readiness 检查。
	- 对缺失 key 场景返回明确 4xx（建议 422），避免通用 500。

2. 观测字段增强：
	- 在 activation / metrics 中补充 `provider_ready`、`provider_name`、`block_reason`。
	- 使 smoke 报告可直接识别是 memory 回归还是 provider 配置问题。

3. 文档补齐：
	- 在 API 参考文档增加“最小可运行配置（含 deepseek key）”与“无 key 的预期错误码”。

### 9.3 下一轮验收标准

当 deepseek key 配置完成后，下一轮 smoke 以如下标准判定 Plan 生效：

1. `POST /story/generate`（`mode=narrative`）成功，返回 `activation_logs` 且包含至少一项 memory 来源记录。
2. 第二轮生成后 `summary_memory_snapshot` 出现或 `activation_logs` 明确记录 summary update。
3. `DELETE /messages/last` + `POST /regenerate` 路径可用，无会话错位。
4. `POST /generate/stream` 在 `mode=choices` 时返回 `choices` 字段。

---

## 10. 追加记录 A：上次重跑结果（deepseek 默认链路）

执行时间：2026-03-16（晚间）

执行前置：
- `GET /api/v2/health`：200
- `GET /api/v2/providers`（带真实 `X-User-ID`）：`deepseek.available=true`

主链路结果：
- `POST /api/v2/story/session`：200（会话创建成功）
- `POST /api/v2/story/generate`：200（默认 `deepseek-chat`）
- `POST /api/v2/story/generate/stream`（`mode=choices`）：200，done 事件包含 `choices=3`
- `DELETE /api/v2/story/session/{id}/messages/last`：200
- `POST /api/v2/story/session/{id}/regenerate`：200

落库核验（SQLite，`story_rag_service/data/chatbox.db`）：
- `story_session_messages`：会话下消息条目存在（写路径生效）
- `conversation_summaries`：存在该会话摘要行并更新 `updated_at`（semantic 更新生效）

观察到的偏差：
- 非流式返回中的 `activation_logs/contexts/summary_memory_snapshot` 在多数轮次为空。
- 但数据库层已确认 episodic 与 semantic 均发生更新，说明“记忆写入链路已工作”，更像“响应可观测字段与实际写入不同步”。

---

## 11. 追加记录 B：本轮行为验证（对齐 Plan 10.2，行 482-488）

执行时间：2026-03-16（继续复测）

测试会话：`c9fd0c66-f8de-4749-8321-7eb67c89c905`

### 11.1 长会话继续生成

对应验收项：
- recent window、summary 更新、history 召回正常。

执行：连续 4 轮 `POST /api/v2/story/generate`（`mode=narrative`）。

结果：
- 4 轮全部 `200`，模型均为 `deepseek-chat`。
- 文本持续增长（`text_len` 250/301/377/360），连续性正常。
- API 返回层：`activation_log_count=0`、`has_summary_snapshot=false`、`context_count=0`（本场景下未显式暴露）。
- DB 层：`conversation_summaries` 存在该会话记录，`updated_at=2026-03-16T20:01:37.718646`，且摘要内容随会话推进更新。

判定：
- 行为层通过（可连续推进）。
- 可观测层部分不满足预期（响应中 memory 证据不足），需后续补齐 observability 输出一致性。

### 11.2 服务重启恢复 session

对应验收项：
- 服务重启后 raw messages / semantic summary / profile state 不丢。

执行：
1. 停服并重启 8012。
2. 重启后读取同一会话并继续生成。
3. 直接查 SQLite 验证消息与摘要。

结果：
- 重启后 `GET /api/v2/health`：200。
- 重启后 `GET /api/v2/story/session/{id}`：200。
- DB 核验：
	- `story_session_messages` 数量：`12`（未丢失）
	- `conversation_summaries`：存在（未丢失）
- 重启后继续生成：`POST /api/v2/story/generate`：200，`post_restart_activation_log_count=1`。

判定：通过。

### 11.3 roleplay + script design 混合场景（procedural 注入）

对应验收项：
- procedural constraints 仍正确注入。

执行：
- 第一次请求使用 `dialogue_mode=character`，返回 `422`（当前契约允许值：`auto|focused|required`）。
- 修正为 `dialogue_mode=required` 后重试成功。

修正后结果：
- `POST /api/v2/story/generate`：200。
- 输出文本含第一人称与对话风格；`activation_log_count=1`；`has_summary_snapshot=true`。

判定：
- 行为通过。
- 同时记录一条契约风险：`dialogue_mode` 枚举变更需同步 smoke 参数模板。

### 11.4 regenerate / rollback 一致性

对应验收项：
- episodic raw history 与 semantic summary 不明显错位。

执行：
1. 记录 `story_session_messages` 条数（删除前）。
2. `DELETE /messages/last`。
3. `POST /regenerate`。
4. 再次核验条数与摘要。

结果：
- 删除前条数：`10`
- 删除后条数：`9`
- regenerate 后条数：`10`
- `DELETE` 与 `regenerate` 均为 `200`。
- regenerate 生成文本长度：`237`。
- `conversation_summaries` 保持存在并更新。

判定：通过（未见明显错位）。

---

## 12. 本轮结论（针对 Plan 10.2）

结论汇总：
- `长会话继续生成`：通过（行为连续），但响应层 memory 观测字段偏弱。
- `服务重启恢复 session`：通过（DB 证据明确）。
- `roleplay + script design 混合`：通过（修正枚举后）。
- `regenerate / rollback 一致性`：通过（计数与摘要一致）。

当前主要待改进点：
- 将 DB 已生效的 memory 更新信号稳定映射到 API 响应中的 `activation_logs / summary_memory_snapshot / contexts`，避免“行为已生效、观测却不充分”的诊断盲区。
