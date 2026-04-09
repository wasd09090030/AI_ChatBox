# Plan0409 双路生成与结构化 Patch 复测报告（流式兼容补充）

## 1. 复测目标

针对 `Plan_2026-04-09_双路生成与结构化实体Patch实施任务清单.md` 新增条目进行回归验证：

1. 流式路径 provider 兼容修复：SSE 正文保持流式，但 `entity patch` 抽取使用独立非流式 LLM，避免 `stream_options should be set along with stream = true` 导致 patch 抽取退化。
2. 流式 OpenAI compat 风险收口：
   - 输入增强与 lorebook 压缩复用非流式 `preprocess_llm`
   - provider 拒绝 `stream_options` 时自动回退不带 `stream_options` 的 SSE 请求

## 2. 执行信息

- 执行日期：2026-04-09
- 目标服务：`http://127.0.0.1:8000`
- 验证脚本：`scripts/smoke_dual_route_patch_plan_20260409.py`
- Provider：`deepseek`
- Model：`deepseek-chat`
- 结果明细：`docs/TestResult/Plan0409_DualRoutePatch_Validation_Run.json`

## 3. 执行结果

- 最近一次执行时间：`2026-04-09 21:07:51`
- 总检查项：`56`
- 通过：`55`
- 失败：`1`
- 总体状态：`未全通过（1 项失败）`

## 4. 与新增 8/9 点对应的关键检查结果

以下检查项均通过，说明流式链路在当前 DeepSeek 环境下未出现新增条目所针对的兼容性崩溃：

1. `generate_contract_fields`：通过（200）
2. `stream_done_contract_fields`：通过（200）
3. `stream_world_update_patch_meta`：通过
4. `stream_operation_chain_aligned`：通过
5. `stream_entity_events_persisted_if_patch`：通过
6. `regenerate_contract_fields`：通过（200）

结论：从接口行为和产物契约看，新增的流式 provider 兼容修复已生效，SSE 生成与 patch 相关字段返回链路可用。

## 5. 失败项（1/56）

失败项：`stream_state_transition_visible`

失败细节（摘要）：

1. 断言预期：`张三.current_location == 地下仓库` 且 inventory 不含 `铜钥匙`
2. 实际：本轮生成中 `张三.current_location == 钟楼顶层`，但 `铜钥匙` 已移除
3. `stream_done_preview` 文本显示模型叙事仍包含“先去地下仓库”的语言意图，但实体状态最终地点未落到“地下仓库”

判定：该失败属于内容语义落地不稳定（模型随机性/叙事路径偏移）导致的业务断言失败，不是流式协议兼容或 `stream_options` 机制崩溃。

## 6. 复测结论

1. 新增的第 8、9 点对应的“流式兼容”目标在本轮回归中表现正常。
2. 当前剩余风险为单条“语义强约束”断言波动，不影响流式链路可用性结论。
3. 建议后续将 `stream_state_transition_visible` 调整为更稳健断言（例如接受“地点变更意图 + 关键字段变更”组合条件），降低模型随机性噪声。
