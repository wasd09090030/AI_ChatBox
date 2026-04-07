"""
向量库工厂：集中创建 Embedding、Chroma 客户端与 LangChain 向量存储实例。
"""

from __future__ import annotations

import logging

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


def create_embeddings(model_name: str, cache_dir: str) -> HuggingFaceEmbeddings:
    """创建 HuggingFace embedding 实例。"""
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
        raise


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
    embeddings: HuggingFaceEmbeddings,
) -> Chroma:
    """创建 LangChain Chroma 向量存储实例。"""
    return Chroma(
        client=chroma_client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )
