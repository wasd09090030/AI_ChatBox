# Console 与场景化模型选择 Smoke API 验证报告（2026-03-18）

## 1. 目标与依据

本次 smoke API 验证基于文档：
- `story_rag_service/docs/Plan/plan_2026-03-18_控制台目录与场景化模型选择重构方案.md`

验证目标：
1. 校验控制台改造依赖的统计接口可用（`/api/v2/stats/*`）。
2. 校验默认模型选择与场景化模型选择接口可读可写。
3. 校验三条执行链路在 deepseek 配置下可用：
   - 故事生成（`story_generation`）
   - Prompt 优化预览（`input_enhancement`）
   - 故事调整润色（`story_adjustment`）

---

## 2. Smoke 设计

### 2.1 测试脚本

新增脚本：
- `story_rag_service/scripts/smoke_console_scene_models.py`

脚本覆盖 13 个步骤：
1. `GET /api/v2/health`
2. `GET /api/v2/providers`
3. `PUT /api/v2/providers/default-selection`
4. `GET /api/v2/providers/default-selection`
5. `PUT /api/v2/providers/scene-models`
6. `GET /api/v2/providers/scene-models`
7. `GET /api/v2/stats/overview`
8. `GET /api/v2/stats/daily?days=7`
9. `GET /api/v2/stats/log?limit=10`
10. `GET /api/v2/stats/filter-options`
11. `POST /api/v2/story/generate`
12. `POST /api/v2/story/input-enhancement/preview`
13. `POST /api/v2/story/adjustments/polish`

### 2.2 模型与用户选择

按你的要求使用 deepseek：
- provider: `deepseek`
- model: `deepseek-chat`

说明：
- 初次使用临时用户 `smoke-console-user` 执行时，因该用户未配置 key 导致 LLM 链路失败。
- 之后切换到已配置 deepseek key 的真实用户 `user_1773820783085_bk1gzshza` 重跑并全部通过。

---

## 3. 执行环境与命令

- OS: Windows 11（PowerShell）
- Base URL: `http://127.0.0.1:8000`
- 运行命令：

```powershell
$env:SMOKE_USER_ID='user_1773820783085_bk1gzshza'
$env:SMOKE_PROVIDER='deepseek'
$env:SMOKE_MODEL='deepseek-chat'
python scripts/smoke_console_scene_models.py
```

---

## 4. 执行结果

最终结果：`13/13` 通过。

| 步骤 | API | 预期 | 实际 | 结论 |
| --- | --- | --- | --- | --- |
| 1 | GET `/api/v2/health` | 200 + healthy | `{"status":"healthy","api_version":"v2"}` | 通过 |
| 2 | GET `/api/v2/providers` | deepseek 可见 | `deepseek available=True` | 通过 |
| 3 | PUT `/api/v2/providers/default-selection` | 写入 deepseek/deepseek-chat | 返回 provider/model 均为目标值 | 通过 |
| 4 | GET `/api/v2/providers/default-selection` | 读回一致 | 返回 `deepseek` + `deepseek-chat` | 通过 |
| 5 | PUT `/api/v2/providers/scene-models` | 三场景写入成功 | 三场景均保存为 deepseek-chat | 通过 |
| 6 | GET `/api/v2/providers/scene-models` | 回显 + fallback | 回显正确，fallback 正确 | 通过 |
| 7 | GET `/api/v2/stats/overview` | 控制台总览可读 | 返回 `total_requests=23` 等字段 | 通过 |
| 8 | GET `/api/v2/stats/daily` | 控制台趋势可读 | 返回 7 条日统计 | 通过 |
| 9 | GET `/api/v2/stats/log` | 控制台事件日志可读 | 返回 10 条事件 | 通过 |
| 10 | GET `/api/v2/stats/filter-options` | 控制台筛选项可读 | `models=2,event_types=1,world_ids=1` | 通过 |
| 11 | POST `/api/v2/story/generate` | 生成成功 | `model=deepseek-chat`, 文本长度 72 | 通过 |
| 12 | POST `/api/v2/story/input-enhancement/preview` | Prompt 优化成功 | `applied=True` 且有增强文本 | 通过 |
| 13 | POST `/api/v2/story/adjustments/polish` | 润色成功 | `model=deepseek-chat` 且返回 polish 文本 | 通过 |

---

## 5. 关键证据

- 生成会话 `session_id`: `70d2b9fd-694a-4dfe-a422-5a8601975aa9`
- 生成链路返回 `model`: `deepseek-chat`
- Prompt 预览示例：
  - 原文：`他很紧张`
  - 增强：`你注意到他紧握的拳头和急促的呼吸，显然处于高度紧张状态。`
- 调整链路：
  - `story_id`: `3e6bf65f-b0eb-41e3-ac0f-5af8f3f6771e`
  - `segment_id`: `2a3c3d54-cbef-44f1-a778-8172b20bb05e`
  - polish 返回 `model`: `deepseek-chat`

---

## 6. 结论

本轮 smoke API 验证结论：

1. 控制台相关统计 API（总览/趋势/日志/筛选）可用。
2. 默认模型选择与三场景模型选择接口可读可写，回显一致。
3. 在 deepseek 配置下，三条执行链路（故事生成 / Prompt 优化 / 故事调整）均可成功执行。
4. 本次验证确认了“控制台目录 + 场景化模型选择”方案在后端 API 侧的最小可用闭环。
