"""
文本润色服务。

为用户选中的故事片段提供无副作用的 AI 润色。
"""

from __future__ import annotations

import time
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from config import settings
from services.story_generation.llm_factory import create_llm


class StoryAdjustmentService:
    """生成润色后的替换文本，不修改会话状态。"""

    def __init__(self, story_manager, user_manager=None):
        """功能：初始化对象依赖并设置默认运行状态。"""
        self.story_manager = story_manager
        self.user_manager = user_manager

    async def polish_selection(self, request, *, user_id: Optional[str] = None) -> dict[str, Any]:
        """功能：处理 polish selection。"""
        story = self.story_manager.get_story(request.story_id)
        if story is None:
            raise LookupError(f"Story '{request.story_id}' not found")

        segment = next((item for item in story.segments if item.id == request.segment_id), None)
        if segment is None:
            raise LookupError(f"Segment '{request.segment_id}' not found")

        selected_text = (request.selected_text or "").strip()
        if not selected_text:
            raise ValueError("selected_text is required")

        default_max_tokens = int(getattr(settings, "default_max_tokens", 2000) or 2000)

        llm = create_llm(
            model=request.model,
            temperature=request.temperature or settings.default_temperature,
            max_tokens=min(default_max_tokens, 1200),
            user_id=user_id,
            for_streaming=False,
            provider=request.provider,
            base_url=request.base_url,
            user_manager=self.user_manager,
        )

        system_prompt = (
            "你是一名故事编辑助手。"
            "你的任务仅限于改写用户提供的“选中文本”。"
            "不得改变剧情事实、因果关系、人物身份、时态和叙事视角。"
            "不得扩写未选中的句子，不得补充解释、说明、标题、列表或引号。"
            "只输出最终改写后的纯文本。"
        )
        user_prompt = "\n\n".join(
            [
                f"预设润色方向：{request.preset_instruction}",
                f"用户补充要求：{(request.custom_instruction or '无').strip() or '无'}",
                f"上文参考：{(request.before_context or '无').strip() or '无'}",
                f"选中文本：{selected_text}",
                f"下文参考：{(request.after_context or '无').strip() or '无'}",
                "请只返回改写后的选中文本。",
            ]
        )

        start_time = time.perf_counter()
        response = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        generation_time = time.perf_counter() - start_time
        polished_text = str(getattr(response, "content", "") or "").strip()
        if not polished_text:
            raise ValueError("Polish response is empty")

        model_used = getattr(llm, "model_name", None) or request.model or settings.default_model
        return {
            "story_id": request.story_id,
            "segment_id": request.segment_id,
            "original_text": request.selected_text,
            "polished_text": polished_text,
            "model": model_used,
            "generation_time": generation_time,
        }
