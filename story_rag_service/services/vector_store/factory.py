"""
向量库工厂：集中创建 Embedding、Chroma 客户端与 LangChain 向量存储实例。
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from typing import List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings

# 变量作用：模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)


# 变量作用：正则规则 _TOKEN_PATTERN，用于文本模式匹配。
_TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]|[a-zA-Z0-9_-]+")


class LightweightFallbackEmbeddings(Embeddings):
    """离线启动兜底嵌入，避免在无网络环境下阻塞应用启动。"""

    def __init__(self, dimensions: int = 384):
        """功能：初始化对象依赖并设置默认运行状态。"""
        self.dimensions = dimensions

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """功能：处理 embed documents。"""
        return [self._embed_text(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        """功能：处理 embed query。"""
        return self._embed_text(text)

    def _embed_text(self, text: str) -> List[float]:
        """功能：处理 embed text。"""
        vector = [0.0] * self.dimensions
        tokens = _TOKEN_PATTERN.findall((text or "").lower())

        if not tokens:
            vector[0] = 1.0
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for offset in range(0, len(digest), 4):
                chunk = digest[offset : offset + 4]
                if len(chunk) < 4:
                    continue
                value = int.from_bytes(chunk, "little", signed=False)
                index = value % self.dimensions
                sign = 1.0 if value & 1 else -1.0
                vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            vector[0] = 1.0
            return vector
        return [value / norm for value in vector]


def _create_fallback_embeddings() -> Embeddings:
    """功能：创建 fallback embeddings。"""
    logger.warning("Using lightweight offline fallback embeddings; semantic retrieval quality will be reduced")
    return LightweightFallbackEmbeddings()


def create_embeddings(model_name: Optional[str], cache_dir: str) -> Embeddings:
    """创建 HuggingFace embedding 实例。"""
    if not model_name:
        return _create_fallback_embeddings()

    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
            cache_folder=cache_dir,
        )
        logger.info("Embedding model loaded successfully")
        return embeddings
    except Exception as exc:
        logger.error(f"Embedding model load failed: {exc}")
        logger.error("Troubleshooting:")
        logger.error("1. Run: python download_model.py")
        logger.error("2. Upload data/huggingface_cache to server")
        logger.error("3. Or set ALLOW_ONLINE_EMBEDDING_DOWNLOAD=true if the host can access HuggingFace")
        return _create_fallback_embeddings()


def create_chroma_client(persist_directory: str) -> chromadb.PersistentClient:
    """创建 Chroma 持久化客户端。"""
    return chromadb.PersistentClient(
        path=persist_directory,
        settings=ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=True,
        ),
    )


def create_vector_store(
    chroma_client: chromadb.PersistentClient,
    collection_name: str,
    embeddings: Embeddings,
) -> Chroma:
    """创建 LangChain Chroma 向量存储实例。"""
    return Chroma(
        client=chroma_client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )
