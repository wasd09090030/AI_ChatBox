"""后端提示词模板的集中注册入口。"""

from .registry import get_prompt_renderer, render_prompt

# 控制 import * 时可导出的公共符号。
__all__ = ["get_prompt_renderer", "render_prompt"]