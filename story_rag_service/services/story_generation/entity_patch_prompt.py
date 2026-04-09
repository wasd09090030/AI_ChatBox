"""实体 patch 抽取提示词构建。"""

from __future__ import annotations

import json
from typing import Any, Iterable


def _serialize_state_snapshot(items: Iterable[dict[str, Any]]) -> str:
    return json.dumps(list(items), ensure_ascii=False, indent=2)


def build_entity_patch_extraction_prompt(
    *,
    user_input: str,
    generated_text: str,
    current_entity_states: Iterable[dict[str, Any]],
) -> str:
    """构建结构化实体 patch 抽取提示词。"""
    snapshot_json = _serialize_state_snapshot(current_entity_states)
    return f"""
你是一个“故事实体状态变化提取器”。你的任务不是续写故事，而是只根据本轮输入和本轮生成结果，提取人物实体状态变化。

输出必须是严格 JSON，不要输出解释，不要输出 Markdown 代码块。

输出格式：
{{
  "patches": [
    {{
      "entity_id": "角色ID",
      "entity_name": "角色名",
      "field_name": "current_location|inventory|status_tags|companions|short_goal|state_summary",
      "op": "set|add|remove|clear|reset",
      "value": "字段值或数组",
      "evidence_text": "直接支撑该变化的文本证据",
      "source_turn": 1,
      "confidence": 0.0
    }}
  ],
  "warnings": []
}}

规则：
1. 只提取“本轮明确发生的变化”，不要重复输出未变化字段。
2. 如果无法确定，不要猜测，直接跳过该变化。
3. `current_location` 与 `short_goal` 优先使用 `set`。
4. `inventory`、`status_tags`、`companions` 优先使用 `add/remove`。
5. `confidence` 取 0 到 1。
6. 证据必须来自本轮输入或本轮生成文本。

当前实体快照：
{snapshot_json}

本轮用户输入：
{user_input}

本轮生成正文：
{generated_text}
""".strip()
