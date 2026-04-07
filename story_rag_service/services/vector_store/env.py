"""
向量库运行环境准备：负责 HuggingFace 缓存与模型路径决策。
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_DEFAULT_EMBEDDING_CACHE_REPO_DIR = (
    "models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2"
)


def prepare_hf_cache(cache_dir: str) -> str:
    """配置 HuggingFace 缓存目录并返回绝对路径。"""
    abs_cache_dir = os.path.abspath(cache_dir)
    os.environ["HF_HOME"] = abs_cache_dir
    os.environ["TRANSFORMERS_CACHE"] = abs_cache_dir
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.makedirs(abs_cache_dir, exist_ok=True)
    logger.info(f"Using HuggingFace cache directory: {abs_cache_dir}")
    return abs_cache_dir


def _resolve_snapshot_cache_path(cache_dir: str) -> Optional[str]:
    """识别标准 huggingface_hub 快照缓存目录结构。"""
    repo_dir = os.path.join(cache_dir, _DEFAULT_EMBEDDING_CACHE_REPO_DIR)
    refs_main_path = os.path.join(repo_dir, "refs", "main")
    snapshots_dir = os.path.join(repo_dir, "snapshots")

    if os.path.isfile(refs_main_path):
        try:
            revision = open(refs_main_path, encoding="utf-8").read().strip()
        except OSError:
            revision = ""
        if revision:
            snapshot_path = os.path.join(snapshots_dir, revision)
            if os.path.isdir(snapshot_path):
                return snapshot_path

    if os.path.isdir(snapshots_dir):
        for entry in sorted(os.listdir(snapshots_dir), reverse=True):
            snapshot_path = os.path.join(snapshots_dir, entry)
            if os.path.isdir(snapshot_path):
                return snapshot_path

    return None


def resolve_embedding_model(cache_dir: str, embedding_model: Optional[str] = None) -> str:
    """解析最终 embedding 模型路径，优先本地缓存或显式传入模型。"""
    if embedding_model:
        os.environ["TRANSFORMERS_OFFLINE"] = "1" if os.path.exists(embedding_model) else "0"
        return embedding_model

    local_model_path = os.path.join(cache_dir, "models", "paraphrase-multilingual-MiniLM-L12-v2")
    if os.path.exists(local_model_path):
        logger.info(f"Using local embedding model: {local_model_path}")
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_HUB_OFFLINE"] = "1"
        return local_model_path

    snapshot_model_path = _resolve_snapshot_cache_path(cache_dir)
    if snapshot_model_path:
        logger.info(f"Using HuggingFace snapshot cache for embedding model: {snapshot_model_path}")
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_HUB_OFFLINE"] = "1"
        return snapshot_model_path

    logger.warning("Local embedding model not found, trying online download")
    logger.info("If network is unavailable, run download_model.py and upload data/huggingface_cache")
    os.environ["TRANSFORMERS_OFFLINE"] = "0"
    os.environ["HF_HUB_OFFLINE"] = "0"
    return DEFAULT_EMBEDDING_MODEL
