"""
Lorebook 子模块导出。
"""

from services.lorebook.service import LorebookManager

# 变量作用：控制 import * 时可导出的公共符号。
__all__ = ["LorebookManager"]
