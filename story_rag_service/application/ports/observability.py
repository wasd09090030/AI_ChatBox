"""可观测性端口定义。"""

from __future__ import annotations

from typing import Any, Optional, Protocol


class MetricsRecorder(Protocol):
    """记录接口级指标的抽象。"""

    def record(
        self,
        *,
        api_version: str,
        mode: str,
        request_id: str,
        session_id: str,
        world_id: Optional[str],
        generation_time: float,
        retrieved_context_count: int,
        retrieved_history_count: int,
        activation_log_count: int = 0,
        rule_hit_count: int = 0,
        vector_hit_count: int = 0,
        budget_trim_dropped_count: int = 0,
        summary_applied: bool = False,
        summary_updated: bool = False,
        story_state_updated: bool = False,
        story_state_clues_count: int = 0,
        request_total_time: float = 0.0,
        success: bool = True,
        error_type: Optional[str] = None,
    ) -> None:
        """记录一次接口观测事件。"""


class AnalyticsSink(Protocol):
    """记录业务分析事件的抽象。"""

    def record_event(self, event_type: str, **payload: Any) -> None:
        """记录一条业务事件。"""
