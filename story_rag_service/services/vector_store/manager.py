"""
向量库门面服务：保留旧版 VectorStoreManager 的对外接口。
"""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document

from config import settings
from models.lorebook import LorebookEntry
from services.vector_store.documents import build_entry_document, build_entry_documents
from services.vector_store.env import prepare_hf_cache, resolve_embedding_model
from services.vector_store.factory import (
    create_chroma_client,
    create_embeddings,
    create_vector_store,
)
from services.vector_store.results import apply_score_threshold, build_documents_from_collection_get

# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)


class VectorStoreManager:
    """管理 Lorebook 的向量化存储与检索能力。"""

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ):
        """初始化向量存储门面。

        包括：缓存目录准备、embedding 初始化、Chroma 客户端创建与启动恢复处理。
        """
        self.persist_directory = persist_directory or settings.chroma_persist_directory
        self.collection_name = collection_name or settings.collection_name

        cache_dir = prepare_hf_cache(settings.huggingface_cache_dir)
        model_name = resolve_embedding_model(
            cache_dir,
            embedding_model=embedding_model,
            allow_online_download=settings.allow_online_embedding_download,
        )

        self.embeddings = create_embeddings(model_name=model_name, cache_dir=cache_dir)
        self.recovered_from_boot_error = False
        self.recovery_backup_directory: Optional[str] = None
        self._initialize_vector_store()

        logger.info(f"VectorStoreManager initialized with collection: {self.collection_name}")

    def _initialize_vector_store(self) -> None:
        """初始化 Chroma 向量存储，必要时执行可恢复错误自愈。"""
        try:
            self.chroma_client = create_chroma_client(self.persist_directory)
            self.vector_store = create_vector_store(
                chroma_client=self.chroma_client,
                collection_name=self.collection_name,
                embeddings=self.embeddings,
            )
        except Exception as exc:
            if not self._is_recoverable_startup_error(exc):
                raise

            backup_directory = self._quarantine_persist_directory()
            logger.warning(
                "Recoverable Chroma startup failure detected for %s: %s. "
                "Moved old directory to %s and rebuilding vector store from SQLite source of truth.",
                self.persist_directory,
                exc,
                backup_directory,
            )
            self.chroma_client = create_chroma_client(self.persist_directory)
            self.vector_store = create_vector_store(
                chroma_client=self.chroma_client,
                collection_name=self.collection_name,
                embeddings=self.embeddings,
            )
            self.recovered_from_boot_error = True
            self.recovery_backup_directory = backup_directory

    @staticmethod
    def _is_recoverable_startup_error(exc: Exception) -> bool:
        """判断启动异常是否属于可自动恢复场景。"""
        message = str(exc).lower()
        return "table collections already exists" in message

    def _quarantine_persist_directory(self) -> str:
        """隔离损坏的持久化目录并创建干净目录。"""
        persist_path = Path(self.persist_directory)
        persist_path.parent.mkdir(parents=True, exist_ok=True)

        if not persist_path.exists():
            persist_path.mkdir(parents=True, exist_ok=True)
            return str(persist_path)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_path = persist_path.with_name(f"{persist_path.name}_recovered_{timestamp}")
        counter = 1
        while backup_path.exists():
            backup_path = persist_path.with_name(
                f"{persist_path.name}_recovered_{timestamp}_{counter}"
            )
            counter += 1

        shutil.move(str(persist_path), str(backup_path))
        persist_path.mkdir(parents=True, exist_ok=True)
        return str(backup_path)

    def add_entry(self, entry: LorebookEntry) -> str:
        """写入单条 lorebook 条目到向量库。"""
        document = build_entry_document(entry)
        target_id = str(entry.id or entry.name)
        ids = self.vector_store.add_documents([document], ids=[target_id])
        logger.info(f"Added entry '{entry.name}' to vector store with ID: {ids[0]}")
        return ids[0]

    def add_entries(self, entries: List[LorebookEntry]) -> List[str]:
        """批量写入 lorebook 条目到向量库。"""
        documents = build_entry_documents(entries)
        ids = [str(entry.id or entry.name) for entry in entries]
        ids = self.vector_store.add_documents(documents, ids=ids)
        logger.info(f"Added {len(entries)} entries to vector store")
        return ids

    def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """执行相似度检索（仅文档，不含分数）。"""
        results = self.vector_store.similarity_search(
            query=query,
            k=k,
            filter=filter_dict,
        )
        logger.info(f"Search for '{query}' returned {len(results)} results")
        return results

    def search_with_score(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Tuple[Document, float]]:
        """执行相似度检索并返回分数（可按阈值过滤）。"""
        results = self.vector_store.similarity_search_with_score(
            query=query,
            k=k,
            filter=filter_dict,
        )
        filtered = apply_score_threshold(results, score_threshold)
        logger.info(f"Search with score for '{query}' returned {len(filtered)} results")
        return filtered

    def delete_entry(self, entry_id: str) -> bool:
        """删除指定向量文档。"""
        try:
            self.vector_store.delete([entry_id])
            logger.info(f"Deleted entry with ID: {entry_id}")
            return True
        except Exception as exc:
            logger.error(f"Error deleting entry {entry_id}: {exc}")
            return False

    def delete_entries_by_prefix(self, prefix: str) -> int:
        """按 ID 前缀批量删除向量文档。"""
        try:
            collection = self.chroma_client.get_or_create_collection(self.collection_name)
            result = collection.get()
            ids = [str(item) for item in (result.get("ids") or [])]
            target_ids = [item for item in ids if item.startswith(prefix)]
            if target_ids:
                collection.delete(ids=target_ids)
            logger.info("Deleted %d vector-store entries by prefix '%s'", len(target_ids), prefix)
            return len(target_ids)
        except Exception as exc:
            logger.error("Error deleting vector-store entries by prefix %s: %s", prefix, exc)
            raise

    def get_all_entries(self) -> List[Document]:
        """获取当前集合中的全部向量文档。"""
        collection = self.chroma_client.get_or_create_collection(self.collection_name)
        result = collection.get()
        documents = build_documents_from_collection_get(result)
        logger.info(f"Retrieved {len(documents)} entries from vector store")
        return documents

    def clear_all(self) -> bool:
        """清空当前集合中的全部向量文档。"""
        try:
            collection = self.chroma_client.get_or_create_collection(self.collection_name)
            result = collection.get()
            ids = result.get("ids") or []
            if ids:
                collection.delete(ids=ids)
            logger.info("Cleared all entries from vector store")
            return True
        except Exception as exc:
            logger.error(f"Error clearing vector store: {exc}")
            return False

    def rebuild_entries(self, entries: List[LorebookEntry]) -> int:
        """基于 SQLite 真值数据重建 Chroma 集合。"""
        self.clear_all()
        if not entries:
            logger.info("Vector store rebuild skipped because SQLite source has no entries")
            return 0

        documents = build_entry_documents(entries)
        ids = [str(entry.id or entry.name) for entry in entries]
        self.vector_store.add_documents(documents, ids=ids)
        logger.info("Rebuilt vector store with %d lorebook entries", len(ids))
        return len(ids)
