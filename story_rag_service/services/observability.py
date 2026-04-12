"""故事生成关键链路的可观测性辅助模块。"""

from dataclasses import dataclass
from threading import Lock
from typing import Dict, Tuple, Optional
import logging

# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)


@dataclass
class _Counter:
    """单个(api_version, mode)维度下的请求计数器。"""

    total: int = 0
    error: int = 0


class StoryGenerationMetrics:
    """故事生成接口的内存指标记录器。"""

    def __init__(self):
        """初始化线程安全计数器容器。"""
        self._lock = Lock()
        self._counters: Dict[Tuple[str, str], _Counter] = {}

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
        success: bool,
        error_type: Optional[str] = None,
    ) -> None:
        """记录一次故事生成观测数据并输出结构化日志。

        计数器按 `(api_version, mode)` 维度累计，用于计算粗粒度错误率。
        """
        key = (api_version, mode)
        with self._lock:
            counter = self._counters.setdefault(key, _Counter())
            counter.total += 1
            if not success:
                counter.error += 1
            error_rate = counter.error / counter.total if counter.total else 0.0

        # 统一单行日志格式，便于采集系统直接解析关键字段。
        logger.info(
            "metric=story_generation api_version=%s mode=%s request_id=%s session_id=%s world_id=%s success=%s request_time_s=%.3f gen_time_s=%.3f orchestration_overhead_s=%.3f contexts=%s history_hits=%s activation_logs=%s rule_hits=%s vector_hits=%s budget_trim_dropped=%s summary_applied=%s summary_updated=%s story_state_updated=%s story_state_clues=%s error_type=%s total=%s errors=%s error_rate=%.4f",
            api_version,
            mode,
            request_id,
            session_id,
            world_id,
            success,
            request_total_time,
            generation_time,
            max(0.0, request_total_time - generation_time),
            retrieved_context_count,
            retrieved_history_count,
            activation_log_count,
            rule_hit_count,
            vector_hit_count,
            budget_trim_dropped_count,
            summary_applied,
            summary_updated,
            story_state_updated,
            story_state_clues_count,
            error_type or "-",
            counter.total,
            counter.error,
            error_rate,
        )


# 变量 metrics_recorder，用于保存 metrics recorder 相关模块级状态。
metrics_recorder = StoryGenerationMetrics()
