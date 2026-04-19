"""可观测性端口的基础设施适配器。"""

from __future__ import annotations

from typing import Any, Optional

from application.ports import AnalyticsSink, MetricsRecorder
from services import analytics_service
from services.observability import metrics_recorder


class AnalyticsServiceAdapter(AnalyticsSink):
    """把 analytics_service 模块适配为 AnalyticsSink。"""

    def record_event(self, event_type: str, **payload: Any) -> None:
        analytics_service.record_event(event_type=event_type, **payload)


class StoryGenerationMetricsRecorderAdapter(MetricsRecorder):
    """把 metrics_recorder 单例适配为 MetricsRecorder。"""

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
        metrics_recorder.record(
            api_version=api_version,
            mode=mode,
            request_id=request_id,
            session_id=session_id,
            world_id=world_id,
            generation_time=generation_time,
            retrieved_context_count=retrieved_context_count,
            retrieved_history_count=retrieved_history_count,
            activation_log_count=activation_log_count,
            rule_hit_count=rule_hit_count,
            vector_hit_count=vector_hit_count,
            budget_trim_dropped_count=budget_trim_dropped_count,
            summary_applied=summary_applied,
            summary_updated=summary_updated,
            story_state_updated=story_state_updated,
            story_state_clues_count=story_state_clues_count,
            request_total_time=request_total_time,
            success=success,
            error_type=error_type,
        )
