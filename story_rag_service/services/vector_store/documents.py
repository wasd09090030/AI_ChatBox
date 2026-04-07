"""
LorebookEntry 到向量文档的转换逻辑。
"""

from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.documents import Document

from models.lorebook import LorebookEntry


def build_entry_metadata(entry: LorebookEntry) -> Dict[str, Any]:
    """构建用于向量库写入的元数据，并清理 None 值。"""
    metadata: Dict[str, Any] = {
        "id": entry.id or entry.name,
        "world_id": entry.world_id,
        "type": entry.type,
        "name": entry.name,
        "keywords": ",".join(entry.keywords),
        "created_at": entry.created_at.isoformat(),
    }

    for key, value in entry.metadata.items():
        if value is not None:
            metadata[key] = str(value)

    return metadata


def build_entry_document(entry: LorebookEntry) -> Document:
    """构建单条向量文档。"""
    return Document(
        page_content=entry.description,
        metadata=build_entry_metadata(entry),
    )


def build_entry_documents(entries: List[LorebookEntry]) -> List[Document]:
    """批量构建向量文档列表。"""
    return [build_entry_document(entry) for entry in entries]
