"""RAG 会话历史管理。"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from models.lorebook import LorebookEntry
from services.vector_store import VectorStoreManager

# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)


class ConversationHistoryManager:
    """会话历史管理器，负责历史向量写入与检索。"""
    
    def __init__(self, vector_store: VectorStoreManager):
        """初始化会话历史管理器。"""
        self.vector_store = vector_store
        logger.info("ConversationHistoryManager initialized")
    
    def add_message_to_rag(
        self,
        session_id: str,
        world_id: Optional[str],
        role: str,
        content: str,
        turn_number: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """将单条会话消息写入 RAG 向量库。"""
        normalized_world_id = world_id or "global"

        # 将消息标准化为 lorebook-like 文档结构，便于统一向量检索。
        entry = LorebookEntry(
            id=f"history_{session_id}_{turn_number}_{role}",
            world_id=normalized_world_id,
            type="conversation_history",
            name=f"对话记录 #{turn_number}",
            description=f"[{role}]: {content}",
            keywords=[session_id, normalized_world_id, f"turn_{turn_number}"],
            metadata={
                "is_history": True,
                "session_id": session_id,
                "role": role,
                "turn_number": turn_number,
                **(metadata or {})
            },
            created_at=datetime.now()
        )
        
        entry_id = self.vector_store.add_entry(entry)
        logger.info(f"Added conversation turn {turn_number} to RAG for session {session_id}")
        return entry_id
    
    def search_relevant_history(
        self,
        query: str,
        session_id: str,
        world_id: Optional[str],
        k: int = 5,
        min_turn: Optional[int] = None,
        max_turn: Optional[int] = None,
        score_threshold: float = 0.3,
        assistant_weight: float = 1.2
    ) -> List[Dict[str, Any]]:
        """按查询语义检索相关历史消息。

        支持按会话、世界和回合区间过滤，并对 assistant 消息给予排序优先权。
        """
        # Chroma 过滤条件：限定历史条目 + 当前会话（可选世界）。
        filter_dict = {
            "$and": [
                {"is_history": {"$eq": "True"}},
                {"session_id": {"$eq": session_id}}
            ]
        }

        if world_id:
            filter_dict["$and"].append({"world_id": {"$eq": world_id}})
        
        # 先做轻量查询增强，提高剧情动作/引号短语召回率。
        enhanced_query = self._enhance_query_for_history(query)
        logger.info(f"🔍 历史检索增强查询: '{enhanced_query[:100]}...'")
        
        # 召回更多候选后再做业务过滤与加权排序。
        results = self.vector_store.search_with_score(
            query=enhanced_query,
            k=k * 3,  # 先多召回候选，后续再按业务规则筛选与排序。
            filter_dict=filter_dict
        )
        
        # 按回合窗口、相关度阈值、角色权重进行二次筛选。
        filtered_results = []
        for doc, score in results:
            # turn_number 可能以字符串形式存储，先做健壮转换。
            turn_number_raw = doc.metadata.get("turn_number", 0)
            try:
                turn_number = int(turn_number_raw)
            except (ValueError, TypeError):
                turn_number = 0
            
            if min_turn is not None and turn_number < min_turn:
                continue
            if max_turn is not None and turn_number > max_turn:
                continue
            
            # Chroma 返回的是距离分数，越小越相关。
            if score > score_threshold:
                logger.debug(f"跳过低相关度历史: turn={turn_number}, score={score:.3f} > threshold={score_threshold}")
                continue
            
            # 读取角色并应用排序权重。
            role = doc.metadata.get("role", "unknown")
            content = doc.page_content.replace("[user]: ", "").replace("[assistant]: ", "")
            
            # assistant 消息通常含剧情推进信息，默认优先于 user 行动描述。
            # Chroma score 越低越好，因此 user 分数乘权重后会变“更差”。
            weighted_score = score if role == "assistant" else score * assistant_weight
            
            filtered_results.append({
                "role": role,
                "content": content,
                "turn_number": turn_number,
                "relevance_score": score,  # 保留原始分数用于展示。
                "weighted_score": weighted_score,  # 使用加权分数参与排序。
                "metadata": doc.metadata
            })
        
        # 按加权相关度排序并截断到 k。
        filtered_results.sort(key=lambda x: x["weighted_score"])
        final_results = filtered_results[:k]
        
        # 输出检索命中摘要，便于排查召回质量。
        if final_results:
            logger.info(f"📜 检索到 {len(final_results)} 条相关历史对话:")
            for i, hist in enumerate(final_results):
                role_label = "玩家动作" if hist['role'] == 'user' else "故事情节"
                logger.info(f"  {i+1}. [{role_label}] Turn#{hist['turn_number']} (score={hist['relevance_score']:.3f}): {hist['content'][:50]}...")
        else:
            logger.info("📜 未检索到相关历史对话")
        
        return final_results
    
    def _enhance_query_for_history(self, query: str) -> str:
        """增强历史检索查询，补充关键动作与引号短语。"""
        # 轻量启发式增强：保留原句 + 引号短语 + 常见动作词。
        # 该方法故意保持无外部依赖，降低部署复杂度。
        import re
        
        enhanced_parts = [query]
        
        # 引号文本通常是关键名词或目标对象。
        quoted = re.findall(r'["「『]([^"」』]+)["」』]', query)
        enhanced_parts.extend(quoted)
        
        # 常见剧情动作词，用于补充检索语义。
        story_keywords = ['进入', '离开', '发现', '遇到', '攻击', '防御', '对话', '交谈',
                          '战斗', '逃跑', '探索', '调查', '使用', '拿起', '放下', '打开', '关闭']
        for keyword in story_keywords:
            if keyword in query:
                enhanced_parts.append(keyword)
        
        enhanced_query = ' '.join(enhanced_parts)
        return enhanced_query
    
    def delete_session_history(self, session_id: str) -> int:
        """删除指定会话的全部历史条目（当前为占位实现）。"""
        # 该接口仍依赖向量层批量删除能力，当前仅记录告警并返回 0。
        logger.warning(f"Bulk delete not implemented. Session {session_id} history remains in vector store.")
        return 0

    def clear_session_history(self, session_id: str) -> int:
        """按会话前缀删除向量历史条目。"""
        prefix = f"history_{session_id}_"
        return self.vector_store.delete_entries_by_prefix(prefix)

    def rebuild_session_history(self, session_id: str, world_id: Optional[str], messages: List[Any]) -> int:
        """按有序消息重建会话历史向量索引。"""
        self.clear_session_history(session_id)

        rebuilt = 0
        for idx, message in enumerate(messages):
            role = getattr(message, "role", None) or (message.get("role") if isinstance(message, dict) else None)
            content = getattr(message, "content", None) or (message.get("content") if isinstance(message, dict) else None)
            if role not in {"user", "assistant"} or not content:
                continue
            turn_number = idx // 2 + 1
            self.add_message_to_rag(
                session_id=session_id,
                world_id=world_id,
                role=role,
                content=content,
                turn_number=turn_number,
            )
            rebuilt += 1
        return rebuilt
