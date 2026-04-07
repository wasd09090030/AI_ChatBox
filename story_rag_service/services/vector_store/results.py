"""
向量检索结果处理工具。
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from langchain_core.documents import Document


def apply_score_threshold(
    results: List[Tuple[Document, float]],
    score_threshold: Optional[float],
) -> List[Tuple[Document, float]]:
    """按阈值过滤检索分数（Chroma 距离越小越相关）。"""
    if score_threshold is None:
        return results
    return [(doc, score) for doc, score in results if score <= score_threshold]


def build_documents_from_collection_get(result: dict) -> List[Document]:
    """将 Chroma collection.get() 结果转换为 Document 列表。"""
    documents: List[Document] = []
    ids = result.get("ids") or []
    metadatas = result.get("metadatas") or []
    contents = result.get("documents") or []

    for idx, doc_id in enumerate(ids):
        metadata = metadatas[idx] if idx < len(metadatas) and metadatas[idx] else {}
        metadata["_chroma_id"] = doc_id
        page_content = contents[idx] if idx < len(contents) else ""
        documents.append(Document(page_content=page_content, metadata=metadata))

    return documents
