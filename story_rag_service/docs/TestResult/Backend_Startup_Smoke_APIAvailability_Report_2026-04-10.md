# 后端启动、脚本复跑与全接口可用性巡检报告（2026-04-10）

## 1. 执行目标

1. 自行启动后端项目并保留运行日志
2. 在新启动实例上重跑 smoke 脚本
3. 重点记录脚本执行期间后端出现的异常/告警日志
4. 检查后端全部接口可用性
5. 将结果写入 docs 文件夹

## 2. 执行环境与命令

- 工作目录：`E:\CODE\AI_ChatBox`
- 后端启动端口：`8011`（避免与既有 8000 进程冲突）
- 后端启动命令：
  - `$env:API_PORT='8011'; $env:API_RELOAD='false'; e:/CODE/AI_ChatBox/.venv/Scripts/python.exe story_rag_service/main.py`
- smoke 复跑命令：
  - `$env:SMOKE_BASE_URL='http://127.0.0.1:8011'; e:/CODE/AI_ChatBox/.venv/Scripts/python.exe story_rag_service/scripts/smoke_story_memory_plan_20260410.py`
- 接口巡检方式：
  - 读取 `/openapi.json`
  - 自动遍历全部 HTTP 路由（GET/POST/PUT/PATCH/DELETE）
  - 以探测请求验证路由可达性，判定口径为“非 5xx 视为接口可用”

## 3. 后端启动与 smoke 结果

### 3.1 后端启动

- 启动成功
- 健康检查可用：`GET /api/v2/health -> 200`

### 3.2 smoke 复跑

- 脚本：`story_rag_service/scripts/smoke_story_memory_plan_20260410.py`
- 结果：`25/25` 全通过
- 执行时间：`2026-04-10 18:27:57`
- 结果文件：`story_rag_service/docs/TestResult/Plan0410_StoryMemoryMerge_Validation_Run.json`

## 4. 脚本执行期异常/告警日志重点

本次日志中未出现 ERROR/Traceback，但出现以下告警：

1. `UserWarning`（stream_options 被转入 model_kwargs）
   - 来源：`story_generator.py`
   - 性质：运行告警（非致命）
2. `langgraph.checkpoint.serde.jsonplus WARNING`
   - 内容：反序列化未注册类型（未来版本可能受限）
   - 涉及类型：`models.story.StoryGenerationRequest`、`models.story.StoryGenerationResponse`
   - 性质：兼容性前瞻告警（当前不阻断）

详细摘录见：
- `story_rag_service/docs/TestResult/Backend_RunDuringSmoke_AnomalyLog_2026-04-10.log`

## 5. 全接口可用性巡检结果

- OpenAPI 加载：成功（200）
- 探测路由总数：`69`
- 可用路由数：`69`
- 不可用路由数：`0`
- 状态码分布：
  - `200`: 35
  - `400`: 4
  - `404`: 29
  - `422`: 1

说明：

1. `400/404/422` 主要来自探测时的占位参数或资源不存在，属于“路由可达但业务校验未通过”的预期结果
2. 本次未发现 5xx 和请求异常超时，不存在接口不可达项

巡检明细见：
- `story_rag_service/docs/TestResult/Backend_ApiAvailability_Check_2026-04-10.json`
- `story_rag_service/docs/TestResult/Backend_ApiAvailability_NonHealthy_Details_2026-04-10.md`（非 200 明细日志）

## 6. 结论

1. 已成功自行启动后端并完成 smoke 复跑
2. smoke 全量通过（25/25）
3. 脚本执行期间未出现致命异常（无 ERROR、无 Traceback）
4. 全量 OpenAPI 路由巡检显示接口整体可用（69/69，0 个不可用）
5. 建议后续处理两类告警：
   - `stream_options` 参数告警（检查调用参数规范）
   - LangGraph checkpoint 未注册类型告警（提前补充允许类型配置，规避未来版本风险）
