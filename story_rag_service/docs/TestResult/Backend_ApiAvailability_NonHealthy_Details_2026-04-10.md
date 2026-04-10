# 后端接口非 200 状态明细日志（2026-04-10）

## 1. 统计

- 数据源：story_rag_service/docs/TestResult/Backend_ApiAvailability_Check_2026-04-10.json
- 提取范围：all_results 中 status != 200 的记录
- 非 200 总数：34
- 400：4
- 404：29
- 422：1

## 2. 详细记录

### 2.1 HTTP 400（4 条）

| 序号 | Method | 路由模板 | 探测路径 | 状态码 | body_required | query_params_used | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | GET | /api/v2/providers/{provider}/models | /api/v2/providers/probe/models | 400 | False | {} | - |
| 2 | PUT | /api/v2/providers/default-selection | /api/v2/providers/default-selection | 400 | True | {} | - |
| 3 | PUT | /api/v2/providers/scene-models | /api/v2/providers/scene-models | 400 | True | {} | - |
| 4 | POST | /api/v2/story/session/{session_id}/entity-state/rebuild | /api/v2/story/session/probe/entity-state/rebuild | 400 | False | {} | - |

### 2.2 HTTP 404（29 条）

| 序号 | Method | 路由模板 | 探测路径 | 状态码 | body_required | query_params_used | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | GET | /api/client-storage/{key} | /api/client-storage/probe | 404 | False | {} | - |
| 2 | DELETE | /api/v2/roleplay/personas/{persona_id} | /api/v2/roleplay/personas/probe | 404 | False | {} | - |
| 3 | GET | /api/v2/roleplay/personas/{persona_id} | /api/v2/roleplay/personas/probe | 404 | False | {} | - |
| 4 | PUT | /api/v2/roleplay/personas/{persona_id} | /api/v2/roleplay/personas/probe | 404 | True | {} | - |
| 5 | GET | /api/v2/roleplay/story-state/{session_id} | /api/v2/roleplay/story-state/probe | 404 | False | {} | - |
| 6 | POST | /api/v2/script-designs | /api/v2/script-designs | 404 | True | {} | - |
| 7 | DELETE | /api/v2/script-designs/{script_design_id} | /api/v2/script-designs/probe | 404 | False | {} | - |
| 8 | GET | /api/v2/script-designs/{script_design_id} | /api/v2/script-designs/probe | 404 | False | {} | - |
| 9 | PUT | /api/v2/script-designs/{script_design_id} | /api/v2/script-designs/probe | 404 | True | {} | - |
| 10 | GET | /api/v2/script-designs/{script_design_id}/story-bindings | /api/v2/script-designs/probe/story-bindings | 404 | False | {} | - |
| 11 | POST | /api/v2/stories | /api/v2/stories | 404 | True | {} | - |
| 12 | DELETE | /api/v2/stories/{story_id} | /api/v2/stories/probe | 404 | False | {} | - |
| 13 | GET | /api/v2/stories/{story_id} | /api/v2/stories/probe | 404 | False | {} | - |
| 14 | PUT | /api/v2/stories/{story_id} | /api/v2/stories/probe | 404 | True | {} | - |
| 15 | POST | /api/v2/stories/{story_id}/adjustments/commit | /api/v2/stories/probe/adjustments/commit | 404 | True | {} | - |
| 16 | GET | /api/v2/stories/{story_id}/entity-state | /api/v2/stories/probe/entity-state | 404 | False | {} | - |
| 17 | POST | /api/v2/stories/{story_id}/entity-state/rebuild | /api/v2/stories/probe/entity-state/rebuild | 404 | False | {} | - |
| 18 | PUT | /api/v2/stories/{story_id}/progress | /api/v2/stories/probe/progress | 404 | True | {} | - |
| 19 | GET | /api/v2/stories/{story_id}/runtime | /api/v2/stories/probe/runtime | 404 | False | {} | - |
| 20 | PUT | /api/v2/stories/{story_id}/runtime | /api/v2/stories/probe/runtime | 404 | True | {} | - |
| 21 | POST | /api/v2/stories/{story_id}/segments | /api/v2/stories/probe/segments | 404 | True | {} | - |
| 22 | DELETE | /api/v2/stories/{story_id}/segments/last | /api/v2/stories/probe/segments/last | 404 | False | {} | - |
| 23 | POST | /api/v2/story/adjustments/polish | /api/v2/story/adjustments/polish | 404 | True | {} | - |
| 24 | DELETE | /api/v2/worlds/{world_id} | /api/v2/worlds/probe | 404 | False | {} | - |
| 25 | GET | /api/v2/worlds/{world_id} | /api/v2/worlds/probe | 404 | False | {} | - |
| 26 | PUT | /api/v2/worlds/{world_id} | /api/v2/worlds/probe | 404 | True | {} | - |
| 27 | POST | /api/v2/worlds/{world_id}/lorebook/character | /api/v2/worlds/probe/lorebook/character | 404 | True | {} | - |
| 28 | POST | /api/v2/worlds/{world_id}/lorebook/event | /api/v2/worlds/probe/lorebook/event | 404 | True | {} | - |
| 29 | POST | /api/v2/worlds/{world_id}/lorebook/location | /api/v2/worlds/probe/lorebook/location | 404 | True | {} | - |

### 2.3 HTTP 422（1 条）

| 序号 | Method | 路由模板 | 探测路径 | 状态码 | body_required | query_params_used | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | PUT | /api/v2/lorebook/entry/{entry_id} | /api/v2/lorebook/entry/probe | 422 | True | {} | - |

## 3. 说明

- 本日志为接口探测记录，不代表业务失败。
- 404 多为占位资源不存在；400/422 多为探测体与真实业务校验不匹配。
- 本次非 200 记录均未出现请求异常（error 为空），接口可达。
