# 全接口功能尝试脚本复跑执行记录（2026-04-10）

## 1. 本次操作

1. 清理上一轮产物：
   - story_rag_service/docs/TestResult/AllApiFunctional_Attempt_Run_2026-04-10.json
   - story_rag_service/docs/TestResult/AllApiFunctional_Attempt_Report_2026-04-10.md
   - story_rag_service/docs/TestResult/AllApiFunctional_Attempt_Execution_Record_2026-04-10.md
2. 启动后端服务（8012）
3. 运行更新后的脚本
4. 记录本次新结果

## 2. 启动与运行命令

- 服务启动命令：
  - $env:API_PORT='8012'; $env:API_RELOAD='false'; .\.venv\Scripts\python.exe story_rag_service\main.py
- 健康检查：
  - GET http://127.0.0.1:8012/api/v2/health -> 200
- 脚本运行命令：
  - $env:SMOKE_BASE_URL='http://127.0.0.1:8012'; .\.venv\Scripts\python.exe story_rag_service\scripts\smoke_all_api_functional_attempt_20260410.py

## 3. 新结果摘要

- base_url: http://127.0.0.1:8012
- openapi_status: 200
- total_endpoints: 69
- PASS: 69
- WARN: 0
- SKIP: 0
- FAIL: 0
- transport_available_endpoints: 69
- executed_at: 2026-04-10 19:57:25

## 4. 结果结论

- 本次 69 个接口全部达到 PASS，无 WARN、无 FAIL。
- 说明你针对 7 个告警来源的定向修复在本轮回归中已生效。

## 5. 产物文件

- JSON：story_rag_service/docs/TestResult/AllApiFunctional_Attempt_Run_2026-04-10.json
- 报告：story_rag_service/docs/TestResult/AllApiFunctional_Attempt_Report_2026-04-10.md
- 执行记录：story_rag_service/docs/TestResult/AllApiFunctional_Attempt_Execution_Record_2026-04-10.md
