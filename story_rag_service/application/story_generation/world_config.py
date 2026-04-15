"""世界配置读取逻辑。

负责读取世界层风格参数并转为 prompt 可消费字典；
读取失败或 world 缺失时返回 None，由上游走默认风格策略。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)


def load_world_config(
    world_manager: Optional[Any],
    world_id: Optional[str],
    log_prefix: str = "",
) -> Optional[Dict[str, Any]]:
    """加载世界风格与氛围配置。"""
    if not world_id or not world_manager:
        return None

    try:
        world = world_manager.get_world(world_id)
        if not world:
            return None

        if log_prefix:
            logger.info("%sLoaded world config: %s", log_prefix, world_id)

        # 返回字段与 prompt_builder 的 world_config 消费字段保持一致。
        return {
            "style_preset": world.style_preset,
            "narrative_tone": world.narrative_tone,
            "pacing_style": world.pacing_style,
            "vocabulary_style": world.vocabulary_style,
            "style_tags": world.style_tags,
            "default_time_of_day": world.default_time_of_day,
            "default_weather": world.default_weather,
            "default_mood": world.default_mood,
        }
    except Exception as exc:
        logger.warning("Failed to load world config: %s", exc)
        return None
