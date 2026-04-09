# Plan0409 双路生成与结构化 Patch 验证报告（复跑）

## 1. 执行信息

- 执行日期：2026-04-09
- 执行时间：2026-04-09 20:30:35
- 验证脚本：scripts/smoke_dual_route_patch_plan_20260409.py
- 目标服务：http://127.0.0.1:8000
- Provider：deepseek
- Model：deepseek-chat
- 数据库：E:\CODE\AI_ChatBox\story_rag_service\data\chatbox.db

## 2. 结果总览

- 总检查项：56
- 通过：56
- 失败：0
- 总体结论：全部通过

## 3. 关键结论

1. 生成链路通过：generate、stream、regenerate 三条主路径返回契约均满足预期。
2. 结构化 patch 通过：entity_state_updates 与 world_update 字段级断言通过。
3. operation chain 通过：memory update 与 entity patch 的 operation_id/sequence 对齐通过。
4. 回放与重建通过：rollback、session rebuild、story rebuild、story segment rollback、adjustment commit 相关断言通过。
5. 存储一致性通过：entity_state_events 表结构与事件持久化断言通过，删除 story 后清理断言通过。

## 4. 产物文件

- 运行明细 JSON：docs/TestResult/Plan0409_DualRoutePatch_Validation_Run.json
- 本报告：docs/TestResult/Plan0409_DualRoutePatch_Validation_Report_2026-04-09.md

## 5. 备注

- 本次复跑前已修复脚本中的分页参数上限问题（timeline 查询 page_size 从 300 调整为 200），避免 422 伪失败影响验收结果。
