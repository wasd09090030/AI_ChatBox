"""
兼容层：保留历史导入路径 `services.lorebook_manager`。

真实实现位于 `services.lorebook.service`。
"""

from services.lorebook import LorebookManager

__all__ = ["LorebookManager"]
