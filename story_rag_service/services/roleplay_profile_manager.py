"""
兼容层：保留历史导入路径 `services.roleplay_profile_manager`。
"""

from services.roleplay_profiles import RoleplayProfileManager

# 控制 import * 时可导出的公共符号。
__all__ = ["RoleplayProfileManager"]
