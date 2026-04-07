"""后端提示词模板的集中注册入口。"""

from .registry import get_prompt_renderer, render_prompt

__all__ = ["get_prompt_renderer", "render_prompt"]