"""
Lorebook 业务服务：负责业务编排与向量检索协同。
"""

from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Optional
from uuid import uuid4

from models.lorebook import Character, Event, Location, LorebookEntry, LorebookType
from services.lorebook.sqlite_store import LorebookSqliteStore
from services.vector_store import VectorStoreManager

# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)


class LorebookManager:
    """知识库管理器：SQLite 作为真值源，ChromaDB 负责语义检索。"""

    def __init__(self, vector_store: VectorStoreManager, db_path: Optional[str] = None):
        """初始化双写存储管理器并在需要时从 SQLite 重建向量索引。"""
        self.vector_store = vector_store
        self._sqlite = LorebookSqliteStore(db_path)
        self.db_path = self._sqlite.db_path
        self._rebuild_vector_store_from_sqlite_if_needed()
        logger.info("LorebookManager initialized (SQLite+ChromaDB double-write)")

    # 兼容旧私有方法接口
    def _ensure_raw_metadata_column(self) -> None:
        """兼容旧接口：确保 SQLite 表具备 raw_metadata 列。"""
        self._sqlite.ensure_raw_metadata_column()

    def _connect(self):
        """兼容旧接口：返回 SQLite 连接。"""
        return self._sqlite.connect()

    def _write_sqlite(
        self,
        entry: LorebookEntry,
        chroma_ref: Optional[str] = None,
        owner_user_id: Optional[str] = None,
    ) -> None:
        """兼容旧接口：写入/覆盖 SQLite 条目。"""
        self._sqlite.upsert_entry(entry, chroma_ref=chroma_ref, owner_user_id=owner_user_id)

    def _delete_sqlite(self, entry_id: str, owner_user_id: Optional[str] = None) -> None:
        """兼容旧接口：删除 SQLite 条目。"""
        self._sqlite.delete_entry(entry_id, owner_user_id=owner_user_id)

    def _get_sqlite_metadata(self, entry_id: str, owner_user_id: Optional[str] = None) -> Dict[str, Any]:
        """兼容旧接口：读取 SQLite 中的启用/优先级元数据。"""
        return self._sqlite.get_metadata(entry_id, owner_user_id=owner_user_id)

    def _list_sqlite_by_world(
        self,
        world_id: Optional[str] = None,
        owner_user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """兼容旧接口：按世界枚举 SQLite 条目。"""
        return self._sqlite.list_entries(world_id, owner_user_id=owner_user_id)

    def _rebuild_vector_store_from_sqlite_if_needed(self) -> None:
        """在向量库异常恢复后，以 SQLite 为真值重建向量索引。"""
        if not getattr(self.vector_store, "recovered_from_boot_error", False):
            return

        rows = self._sqlite.list_entries()
        if not rows:
            logger.info("Chroma recovery completed with empty SQLite lorebook source")
            return

        entries: List[LorebookEntry] = []
        for row in rows:
            try:
                entries.append(
                    LorebookEntry(
                        id=row.get("id"),
                        world_id=str(row.get("world_id") or "global"),
                        type=row.get("type") or LorebookType.CUSTOM,
                        name=str(row.get("name") or "Unnamed"),
                        description=str(row.get("content") or row.get("description") or ""),
                        keywords=list(row.get("keywords") or []),
                        metadata=dict(row.get("metadata") or {}),
                    )
                )
            except Exception as exc:
                logger.warning("Skipped lorebook SQLite row during Chroma rebuild: %s", exc)

        rebuilt_count = self.vector_store.rebuild_entries(entries)
        logger.info("Rebuilt Chroma index from SQLite with %d entries", rebuilt_count)

    def create_entry(self, entry: LorebookEntry, owner_user_id: Optional[str] = None) -> str:
        """创建 lorebook 条目并执行双写。

        主流程先写向量库，再尝试写 SQLite；SQLite 失败仅告警，不阻断请求。
        """
        if not entry.id:
            entry.id = str(uuid4())
        doc_id = self.vector_store.add_entry(entry)
        try:
            self._sqlite.upsert_entry(entry, chroma_ref=doc_id, owner_user_id=owner_user_id)
        except Exception as exc:
            # 双写中的 SQLite 失败不应影响主链路可用性。
            logger.warning(f"SQLite write for entry {entry.id} failed: {exc}")
        logger.info(f"Created lorebook entry: {entry.name} ({entry.type})")
        return entry.id

    def create_character(
        self,
        character: Character,
        world_id: Optional[str] = None,
        owner_user_id: Optional[str] = None,
    ) -> str:
        """将角色对象转换为 lorebook 条目后创建。"""
        target_world_id = world_id or "global"
        entry = character.to_lorebook_entry(target_world_id)
        return self.create_entry(entry, owner_user_id=owner_user_id)

    def create_location(
        self,
        location: Location,
        world_id: Optional[str] = None,
        owner_user_id: Optional[str] = None,
    ) -> str:
        """将地点对象转换为 lorebook 条目后创建。"""
        target_world_id = world_id or "global"
        entry = location.to_lorebook_entry(target_world_id)
        return self.create_entry(entry, owner_user_id=owner_user_id)

    def create_event(
        self,
        event: Event,
        world_id: Optional[str] = None,
        owner_user_id: Optional[str] = None,
    ) -> str:
        """将事件对象转换为 lorebook 条目后创建。"""
        target_world_id = world_id or "global"
        entry = event.to_lorebook_entry(target_world_id)
        return self.create_entry(entry, owner_user_id=owner_user_id)

    def batch_create_entries(self, entries: List[LorebookEntry], owner_user_id: Optional[str] = None) -> List[str]:
        """批量创建条目并执行批量向量写入。"""
        for entry in entries:
            if not entry.id:
                entry.id = str(uuid4())

        self.vector_store.add_entries(entries)
        for entry in entries:
            try:
                self._sqlite.upsert_entry(entry, owner_user_id=owner_user_id)
            except Exception as exc:
                logger.warning(f"SQLite batch write for {entry.id} failed: {exc}")

        logger.info(f"Created {len(entries)} lorebook entries")
        return [entry.id for entry in entries]

    def search_relevant_entries(
        self,
        query: str,
        world_id: Optional[str] = None,
        k: int = 5,
        entry_type: Optional[LorebookType] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """检索相关条目并融合 SQLite 元数据策略。

        检索基于向量库结果，随后按 SQLite 中的 enabled/probability 等规则做过滤。
        """
        filter_dict: Dict[str, Any] = {}
        if world_id:
            filter_dict["world_id"] = world_id
        if entry_type:
            filter_dict["type"] = entry_type.value
        filter_dict = filter_dict if filter_dict else None

        results = self.vector_store.search_with_score(
            query=query, k=k, filter_dict=filter_dict, score_threshold=score_threshold
        )

        formatted_results = []
        for doc, score in results:
            entry_id = doc.metadata.get("id") or doc.metadata.get("_chroma_id", "")
            sqlite_meta = self._sqlite.get_metadata(entry_id)
            if not sqlite_meta.get("enabled", True):
                continue

            prob = float(sqlite_meta.get("probability", 1.0))
            if prob < 1.0 and random.random() > prob:
                continue

            merged_meta = dict(doc.metadata)
            merged_meta.update(sqlite_meta)
            formatted_results.append(
                {
                    "name": doc.metadata.get("name", "Unknown"),
                    "type": doc.metadata.get("type", "unknown"),
                    "content": doc.page_content,
                    "relevance_score": float(score),
                    "insertion_position": sqlite_meta.get("insertion_position", "after_char"),
                    "metadata": merged_meta,
                }
            )

        logger.info(f"Found {len(formatted_results)} relevant entries for query: {query[:50]}...")
        return formatted_results

    def get_all_entries(
        self,
        world_id: Optional[str] = None,
        owner_user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取条目全量列表，优先 SQLite，失败时回退 Chroma。"""
        try:
            entries = self._sqlite.list_entries(world_id, owner_user_id=owner_user_id)
            if entries:
                return entries
        except Exception as exc:
            logger.warning(f"SQLite list_entries failed, falling back to ChromaDB: {exc}")

        docs = self.vector_store.get_all_entries()
        entries = []
        for doc in docs:
            raw_keywords = doc.metadata.get("keywords", "")
            keywords = [k.strip() for k in raw_keywords.split(",") if k.strip()] if raw_keywords else []
            entry = {
                "id": doc.metadata.get("_chroma_id"),
                "world_id": doc.metadata.get("world_id", ""),
                "name": doc.metadata.get("name", "Unknown"),
                "type": doc.metadata.get("type", "unknown"),
                "description": doc.page_content,
                "content": doc.page_content,
                "keywords": keywords,
                "enabled": True,
                "priority": 0,
                "insertion_position": "after_char",
                "probability": 1.0,
                "metadata": doc.metadata,
            }
            if world_id is None or doc.metadata.get("world_id") == world_id:
                entries.append(entry)
        return entries

    def update_entry(self, entry_id: str, new_entry: LorebookEntry, owner_user_id: Optional[str] = None) -> bool:
        """覆盖更新条目（删除旧向量后重建）。"""
        self.vector_store.delete_entry(entry_id)
        new_entry.id = entry_id
        doc_id = self.vector_store.add_entry(new_entry)
        try:
            self._sqlite.upsert_entry(new_entry, chroma_ref=doc_id, owner_user_id=owner_user_id)
        except Exception as exc:
            logger.warning(f"SQLite update for entry {entry_id} failed: {exc}")
        logger.info(f"Updated lorebook entry: {entry_id}")
        return True

    def get_entries_by_world(self, world_id: str, owner_user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """按世界筛选 lorebook 条目。"""
        return self.get_all_entries(world_id=world_id, owner_user_id=owner_user_id)

    def get_entries_by_ids(
        self,
        entry_ids: List[str],
        world_id: Optional[str] = None,
        owner_user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """按显式 id 顺序解析条目列表。"""
        normalized_ids = [str(entry_id).strip() for entry_id in entry_ids if str(entry_id).strip()]
        if not normalized_ids:
            return []

        entries = self.get_all_entries(world_id=world_id, owner_user_id=owner_user_id)
        entry_lookup = {
            str(entry.get("id") or "").strip(): entry
            for entry in entries
            if str(entry.get("id") or "").strip()
        }
        resolved = [entry_lookup[entry_id] for entry_id in normalized_ids if entry_id in entry_lookup]
        missing_ids = [entry_id for entry_id in normalized_ids if entry_id not in entry_lookup]
        if missing_ids:
            logger.info("Skipped %d explicit lorebook entries not found in world=%s", len(missing_ids), world_id)
        return resolved

    def delete_entry(self, entry_id: str, owner_user_id: Optional[str] = None) -> bool:
        """删除单条条目（向量库+SQLite）。"""
        success = self.vector_store.delete_entry(entry_id)
        try:
            self._sqlite.delete_entry(entry_id, owner_user_id=owner_user_id)
        except Exception as exc:
            logger.warning(f"SQLite delete for entry {entry_id} failed: {exc}")
        if success:
            logger.info(f"Deleted lorebook entry: {entry_id}")
        return success

    def clear_all_entries(self) -> bool:
        """清空全部条目（向量库+SQLite）。"""
        success = self.vector_store.clear_all()
        try:
            self._sqlite.clear_all()
        except Exception as exc:
            logger.warning(f"SQLite clear_all failed: {exc}")
        if success:
            logger.info("Cleared all lorebook entries")
        return success

    def delete_entries_by_world(self, world_id: str, owner_user_id: Optional[str] = None) -> int:
        """删除指定世界下的全部条目，返回删除计数。"""
        entries = self.get_all_entries(world_id=world_id, owner_user_id=owner_user_id)
        deleted_count = 0
        for entry in entries:
            entry_id = entry.get("id")
            if entry_id and self.delete_entry(entry_id, owner_user_id=owner_user_id):
                deleted_count += 1
        logger.info(f"Deleted {deleted_count} lorebook entries from world: {world_id}")
        return deleted_count

    def initialize_sample_lorebook(self):
        """初始化示例 lorebook 数据（用于演示或本地调试）。"""
        sample_character = Character(
            name="艾莉亚",
            age=22,
            gender="女",
            appearance="银色长发,翠绿色眼睛,身材纤细",
            personality="勇敢、善良、机智,有时会冲动",
            background="来自北方王国的年轻冒险者,父母在战争中失踪,独自踏上寻找真相的旅程",
            relationships={"托马斯": "童年好友,现为王国骑士", "暗影商人": "神秘的情报贩子,亦敌亦友"},
            abilities=["剑术精通", "基础魔法", "野外生存"],
            current_location="起始村庄",
        )
        sample_location = Location(
            name="起始村庄",
            description="一个宁静的小村庄,位于王国边境,被森林和山脉环绕",
            region="北方王国边境",
            climate="温带,四季分明",
            population=200,
            notable_features=["古老的石桥", "村长的大宅", "铁匠铺", "小酒馆"],
            connected_locations=["迷雾森林", "王都"],
            inhabitants=["村长老约翰", "铁匠哈尔", "酒馆老板娘玛莎"],
        )
        sample_event = Event(
            name="暗影降临",
            description="三个月前,村庄附近的森林开始出现不祥的黑雾,村民报告有怪物出没",
            time="三个月前",
            location="起始村庄附近的迷雾森林",
            participants=["村民", "失踪的猎人", "未知的黑暗势力"],
            consequences="村庄陷入恐慌,多名猎人失踪,通往王都的道路变得危险",
            importance=8,
        )
        self.create_character(sample_character)
        self.create_location(sample_location)
        self.create_event(sample_event)
