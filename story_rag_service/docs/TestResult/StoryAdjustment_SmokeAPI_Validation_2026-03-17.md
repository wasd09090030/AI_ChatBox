# Story Adjustment Smoke API 验证报告（2026-03-17）

## 1. 目标与依据

本文基于 [story_rag_service/docs/TestDoc/StoryAdjustment_Smoke_Windows_2026-03-17.md](story_rag_service/docs/TestDoc/StoryAdjustment_Smoke_Windows_2026-03-17.md) 设计并执行后端 API 级 smoke，验证“故事调整”最小可用链路。

本轮重点覆盖：
- 后端启动与健康状态
- provider 可用性与连通性（deepseek）
- story adjustment polish（草稿态）
- adjustments commit（正式落库 + 一致性重建）
- commit 后继续续写是否承接新上下文
- 刷新后内容持久性

---

## 2. 覆盖范围（API）

- [story_rag_service/api/v2/story/adjustment_routes.py](story_rag_service/api/v2/story/adjustment_routes.py)
- [story_rag_service/api/v2/world_story_routes.py](story_rag_service/api/v2/world_story_routes.py)
- [story_rag_service/services/story_adjustment_service.py](story_rag_service/services/story_adjustment_service.py)
- [story_rag_service/services/story_consistency_rebuild_service.py](story_rag_service/services/story_consistency_rebuild_service.py)

说明：
- 本文是后端 API smoke，不直接覆盖前端本地草稿 UI 行为（例如“撤销本地改动”按钮视觉状态）。

---

## 3. Smoke API 设计

### 3.1 前置检查

1. `GET /api/v2/health`
2. `GET /api/v2/providers`（带 `X-User-ID`）
3. `POST /api/v2/providers/test-connection`（provider=deepseek）

### 3.2 测试数据准备

1. `POST /api/v2/worlds` 创建独立世界
2. `POST /api/v2/stories` 创建故事
3. `POST /api/v2/stories/{story_id}/segments` 添加两段测试文本

### 3.3 故事调整草稿链路

1. `POST /api/v2/story/adjustments/polish`
2. `GET /api/v2/stories/{story_id}` 验证 polish 后未 commit 前正文不变（草稿态）

### 3.4 保存与重建链路

1. `POST /api/v2/stories/{story_id}/adjustments/commit`
2. `GET /api/v2/stories/{story_id}` 验证正文更新
3. 检查 commit 响应字段：
   - `story`
   - `session_id`
   - `rebuild_summary_reset`
   - `rebuild_history_reindexed`
   - `warnings`

### 3.5 保存后续写与持久性

1. `POST /api/v2/story/generate`（使用 commit 的 `session_id`）
2. `GET /api/v2/stories/{story_id}` 再次确认刷新后文本仍为新版本

---

## 4. 执行结果

执行时间：2026-03-17 14:25（Windows, PowerShell）

| 步骤 | 预期 | 实际 | 结论 |
| --- | --- | --- | --- |
| health | 200 + healthy | 200，返回 healthy | 通过 |
| provider available | deepseek available=true | status=200，deepseek 可用 | 通过 |
| provider test connection | success=true,status=ok | success=true,status=ok, latency=1387ms | 通过 |
| create world | 200 + world id | world_id=79ed3d49-661c-4e66-9d7a-efe81c91dcb4 | 通过 |
| create story | 200 + story id | story_id=7840f241-903b-4a60-8a55-afee7fa9c356 | 通过 |
| add segment 1 | 200 | status=200 | 通过 |
| add segment 2 | 200 | status=200 | 通过 |
| polish selection | 200 + polished_text | polished_text 长度 11 | 通过 |
| polish draft only | 未 commit 前正文不变 | unchanged=True | 通过 |
| commit adjustment | 200 + 重建字段 | rebuild_history_reindexed=True,warnings=[] | 通过 |
| commit persisted | 正文已更新 | persisted=True | 通过 |
| post commit continue | 200 且承接新上下文 | contains_new_marker=True（启发式） | 通过 |
| refresh persistence | 刷新后仍是新正文 | status=200 且内容保持 | 通过 |

---

## 5. 关键证据

- world_id: `79ed3d49-661c-4e66-9d7a-efe81c91dcb4`
- story_id: `7840f241-903b-4a60-8a55-afee7fa9c356`
- segment_id: `ddeb166f-dbe6-42ce-b55c-0b124ff72d41`
- commit session_id: `story-adjust-smoke-1773728710`
- polish 结果：`一把黑曜石钥匙·K-Ω`
- commit 后 segment 内容：`主角拆开信，信里提到阁楼和一把黑曜石钥匙·K-Ω。`
- commit 响应重建字段：
  - `rebuild_summary_reset=false`
  - `rebuild_history_reindexed=true`
  - `warnings=[]`
- commit 后续写预览：
  - `钥匙的代号是K-Ω。主角推开阁楼门...`

---

## 6. 对照原路线结论

与路线文档中的 6 项“通过标准”映射如下：

1. Windows 下前后端可正常启动：
- 后端已验证通过。
- 前端启动与 UI 交互不在本 API smoke 范围内。

2. `/story-adjustment` 可进入并共享当前故事工作区：
- 该项为前端路由/状态共享行为，需 UI smoke 补测。

3. 单段选区润色成功且先进入草稿层：
- API 侧通过“polish 后未 commit 正文不变”得到验证。

4. 撤销本地草稿成功：
- 该项属于前端本地草稿态行为，需 UI smoke 补测。

5. 保存后 `StoryView` 立即显示新文本：
- API 侧已验证 commit 成功并持久化；跨页面即时同步需 UI smoke 补测。

6. 保存后继续续写按新文本上下文推进：
- API 侧已验证 generate 结果承接新关键词（启发式通过）。

---

## 7. 结论

本轮 Story Adjustment API smoke 结论：

- 后端最小可用链路完整通过。
- “polish 仅草稿、commit 才落库、commit 后重建并可续写承接新内容”三条核心行为已由 API 实测验证。
- 对于“撤销本地草稿、跨页面即时显示、路由共享工作区”等前端交互行为，建议按原路线再执行一轮 UI smoke 作为补充闭环。
