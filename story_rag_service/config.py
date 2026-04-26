"""Story RAG 配置模块。"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from pathlib import Path
from typing import Optional

# 项目后端目录（story_rag_service）绝对路径。
BASE_DIR = Path(__file__).resolve().parent
# 默认数据根目录（数据库、向量库、缓存等）。
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    """应用配置项。"""
    
    # 各提供商 API Key
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    qwen_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    # LLM 默认配置
    default_llm_provider: str = "deepseek"
    default_model: str = "deepseek-chat"
    default_embedding_model: str = "text-embedding-ada-002"

    # 提供商默认 Base URL（可被用户级配置覆盖）
    deepseek_base_url: str = "https://api.deepseek.com"
    openai_base_url: str = "https://api.openai.com/v1"
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    anthropic_base_url: str = "https://api.anthropic.com"
    # 多模态 API 地址（例如视觉代理地址）；留空表示禁用图像能力。
    multimodal_api_url: str = ""
    multimodal_model: str = "deepseek-vl"
    
    # 生成参数
    default_temperature: float = 0.95
    default_max_tokens: int = 4000  # 增加到 4000 tokens，约 800-1000 个中文字
    
    # 向量库配置
    chroma_persist_directory: str = str(DATA_DIR / "chroma_db")
    collection_name: str = "story_lorebook"
    
    # HuggingFace 配置
    huggingface_cache_dir: str = str(DATA_DIR / "huggingface_cache")
    allow_online_embedding_download: bool = False
    
    # 数据库配置
    database_path: str = str(DATA_DIR / "chatbox.db")

    # 仓储存储配置
    # 注意：当前运行时强制使用 SQLite；以下字段仅用于迁移兼容。
    storage_backend: str = "sqlite"  # 迁移标记（历史遗留）
    storage_shadow_write_json: bool = False  # 已弃用，仅迁移期保留
    storage_auto_migrate_json_to_sqlite: bool = True
    worlds_json_path: str = str(DATA_DIR / "worlds.json")
    stories_json_path: str = str(DATA_DIR / "stories.json")
    
    # 检索配置
    top_k_results: int = 5
    similarity_threshold: float = 0.7
    enable_reranker: bool = False  # P2: Cross-Encoder 精排开关
    rrf_k: int = 60  # P2: RRF 融合常数

    # 摘要记忆配置
    summary_update_turn_interval: int = 4
    summary_max_chars: int = 1200

    # RP 功能开关（灰度发布/回滚）
    rp_story_state_enabled: bool = True
    rp_summary_memory_enabled: bool = True
    rp_debug_payload_enabled: bool = True
    
    # API 配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    cors_allowed_origins: str = "http://localhost:5175,http://127.0.0.1:5175"

    # Auth 配置
    auth_cookie_name: str = "storybox_session"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    auth_session_ttl_hours: int = 168
    auth_claim_unowned_enabled: bool = True

    # LangGraph Checkpointer 配置
    langgraph_checkpoint_backend: str = "sqlite"  # sqlite | memory
    langgraph_checkpoint_sqlite_path: str = str(DATA_DIR / "langgraph_checkpoints.db")

    @field_validator(
        "chroma_persist_directory",
        "huggingface_cache_dir",
        "database_path",
        "worlds_json_path",
        "stories_json_path",
        "langgraph_checkpoint_sqlite_path",
        mode="before",
    )
    @classmethod
    def resolve_data_paths(cls, value: Optional[str]) -> Optional[str]:
        """规范化配置中的路径字段。

        规则：绝对路径保持不变；相对路径按 BASE_DIR 解析为绝对路径。
        """
        if value is None:
            return None
        path = Path(value)
        if path.is_absolute():
            return str(path)
        return str((BASE_DIR / path).resolve())

    @property
    def cors_origin_list(self) -> list[str]:
        """将逗号分隔的 origin 配置解析为列表。"""
        return [item.strip() for item in self.cors_allowed_origins.split(",") if item.strip()]
    
    class Config:
        """Pydantic Settings 配置：指定环境变量文件与大小写策略。"""
        env_file = str(BASE_DIR / ".env")
        case_sensitive = False


# 全局配置单例：模块导入即完成 `.env` + 默认值装配。
settings = Settings()
