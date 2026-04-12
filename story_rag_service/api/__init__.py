"""
API package exports.
"""

from .v2 import router

# 变量作用：控制 import * 时可导出的公共符号。
__all__ = ["router"]
