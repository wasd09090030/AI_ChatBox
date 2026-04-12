"""
向量库服务导出。
"""

from services.vector_store.manager import VectorStoreManager

# 控制 import * 时可导出的公共符号。
__all__ = ["VectorStoreManager"]
