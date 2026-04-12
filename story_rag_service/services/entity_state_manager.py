"""实体状态管理器：用于结构化追踪故事世界中的实体状态。"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

from application.memory import build_memory_update_event, persist_memory_update_events
from models.entity_state import EntityStateRebuildResponse, EntityStateSnapshot
from models.story import Message
from models.story_runtime import ScriptRuntimeState
from models.stored_story import StoredStory
from repositories.entity_state_repository import SqliteEntityStateRepository

# 变量作用：模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)

# 变量作用：变量 _STATUS_KEYWORDS，用于保存 status keywords 相关模块级状态。
_STATUS_KEYWORDS: dict[str, tuple[str, ...]] = {
    "受伤": ("受伤", "伤口", "流血", "负伤"),
    "警觉": ("警觉", "戒备", "警惕"),
    "疲惫": ("疲惫", "疲倦", "喘息", "气喘"),
    "紧张": ("紧张", "不安", "绷紧"),
    "愤怒": ("愤怒", "恼火", "暴怒"),
    "恐惧": ("恐惧", "害怕", "惊惧"),
    "昏迷": ("昏迷", "失去意识"),
}
# 变量作用：正则规则 _INVENTORY_ADD_PATTERNS，用于文本模式匹配。
_INVENTORY_ADD_PATTERNS: tuple[str, ...] = (
    r"{name}[^。！？\n]{0,18}(?:拿着|握着|攥着|带着|背着|提着|揣着|获得了|捡起了|拾起了)([^，。；！？\n]{1,20})",
    r"{name}[^。！？\n]{0,12}手里(?:拿着|握着|攥着)([^，。；！？\n]{1,20})",
)
# 变量作用：正则规则 _INVENTORY_REMOVE_PATTERNS，用于文本模式匹配。
_INVENTORY_REMOVE_PATTERNS: tuple[str, ...] = (
    r"{name}[^。！？\n]{0,18}(?:丢下了|放下了|失去了|交出了|抛下了)([^，。；！？\n]{1,20})",
)
# 变量作用：正则规则 _GOAL_PATTERNS，用于文本模式匹配。
_GOAL_PATTERNS: tuple[str, ...] = (
    r"{name}[^。！？\n]{0,16}(?:想要|准备|打算|决定|试图)([^，。；！？\n]{2,24})",
)


class EntityStateManager:
    """维护当前实体结构化状态，并支持基于故事材料重建。"""

    def __init__(self, repository: SqliteEntityStateRepository, lorebook_manager=None):
        """初始化实体状态管理器。"""
        self.repository = repository
        self.lorebook_manager = lorebook_manager

    def list_story_states(
        self,
        story_id: str,
        *,
        entity_type: Optional[str] = None,
    ) -> List[EntityStateSnapshot]:
        """按故事维度查询实体状态快照。"""
        return self.repository.list_by_story_id(story_id, entity_type=entity_type)

    def list_session_states(
        self,
        session_id: str,
        *,
        entity_type: Optional[str] = None,
    ) -> List[EntityStateSnapshot]:
        """按会话维度查询实体状态快照。"""
        return self.repository.list_by_session_id(session_id, entity_type=entity_type)

    def delete_story_states(self, story_id: str) -> int:
        """删除指定故事下全部实体状态。"""
        return self.repository.delete_by_story_id(story_id)

    def rebuild_story_state(
        self,
        *,
        story: StoredStory,
        session_id: str,
        runtime_state: Optional[ScriptRuntimeState] = None,
        persist: bool = True,
        source: str = "entity_state_rebuild",
        operation_id: Optional[str] = None,
        sequence_start: int = 1,
    ) -> EntityStateRebuildResponse:
        """从故事分段重建实体状态。

        该流程会遍历每个段落的 prompt/content，抽取角色状态、位置、携带物与短期目标，
        最终按故事维度落库并产出 memory update 事件。
        """
        entries = self._load_world_entries(story.world_id)
        character_lookup = self._build_character_lookup(entries)
        location_lookup = self._build_location_lookup(entries)
        states = self._seed_states(
            story_id=story.id,
            session_id=session_id,
            character_lookup=character_lookup,
            location_lookup=location_lookup,
            runtime_state=runtime_state,
        )

        turn_number = 0
        for segment in story.segments:
            prompt_text = str(segment.prompt or "").strip()
            if prompt_text:
                turn_number += 1
                self._consume_text(
                    story_id=story.id,
                    session_id=session_id,
                    text=prompt_text,
                    turn_number=turn_number,
                    states=states,
                    character_lookup=character_lookup,
                    location_lookup=location_lookup,
                )

            content_text = str(segment.content or "").strip()
            if content_text:
                self._consume_text(
                    story_id=story.id,
                    session_id=session_id,
                    text=content_text,
                    turn_number=turn_number,
                    states=states,
                    character_lookup=character_lookup,
                    location_lookup=location_lookup,
                )

        return self._finalize_rebuild(
            story_id=story.id,
            session_id=session_id,
            states=states,
            persist=persist,
            source=source,
            operation_id=operation_id,
            sequence_start=sequence_start,
        )

    def rebuild_session_state(
        self,
        *,
        session_id: str,
        story_id: str,
        world_id: Optional[str],
        messages: Sequence[Message],
        persist: bool = True,
        source: str = "entity_state_session_rebuild",
        operation_id: Optional[str] = None,
        sequence_start: int = 1,
    ) -> EntityStateRebuildResponse:
        """从会话消息流重建实体状态。

        常用于流式/在线生成后按当前会话文本重算实体状态。
        """
        entries = self._load_world_entries(world_id)
        character_lookup = self._build_character_lookup(entries)
        location_lookup = self._build_location_lookup(entries)
        states = self._seed_states(
            story_id=story_id,
            session_id=session_id,
            character_lookup=character_lookup,
            location_lookup=location_lookup,
            runtime_state=None,
        )

        turn_number = 0
        for message in messages:
            if message.role == "user":
                turn_number += 1
            self._consume_text(
                story_id=story_id,
                session_id=session_id,
                text=message.content,
                turn_number=turn_number or None,
                states=states,
                character_lookup=character_lookup,
                location_lookup=location_lookup,
            )

        return self._finalize_rebuild(
            story_id=story_id,
            session_id=session_id,
            states=states,
            persist=persist,
            source=source,
            operation_id=operation_id,
            sequence_start=sequence_start,
        )

    def _load_world_entries(self, world_id: Optional[str]) -> List[Dict[str, Any]]:
        """加载世界设定条目，失败时返回空列表。"""
        if not self.lorebook_manager:
            return []
        try:
            return list(self.lorebook_manager.get_all_entries(world_id=world_id))
        except Exception as exc:
            logger.warning("Failed to load lorebook entries for entity-state rebuild: %s", exc)
            return []

    @staticmethod
    def _build_character_lookup(entries: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """构建角色名到 lorebook 条目的映射。"""
        lookup: Dict[str, Dict[str, Any]] = {}
        for entry in entries:
            if str(entry.get("type") or "") != "character":
                continue
            name = str(entry.get("name") or "").strip()
            entry_id = str(entry.get("id") or "").strip()
            if not name or not entry_id:
                continue
            lookup[name] = entry
        return lookup

    @staticmethod
    def _build_location_lookup(entries: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """构建地点名到 lorebook 条目的映射。"""
        lookup: Dict[str, Dict[str, Any]] = {}
        for entry in entries:
            if str(entry.get("type") or "") != "location":
                continue
            name = str(entry.get("name") or "").strip()
            if not name:
                continue
            lookup[name] = entry
        return lookup

    def _seed_states(
        self,
        *,
        story_id: str,
        session_id: str,
        character_lookup: Dict[str, Dict[str, Any]],
        location_lookup: Dict[str, Dict[str, Any]],
        runtime_state: Optional[ScriptRuntimeState],
    ) -> Dict[str, EntityStateSnapshot]:
        """基于运行时状态初始化种子实体快照。"""
        states: Dict[str, EntityStateSnapshot] = {}
        if runtime_state is None:
            return states

        runtime_location = None
        if runtime_state.current_location_entry_id:
            for location_entry in location_lookup.values():
                if str(location_entry.get("id")) == runtime_state.current_location_entry_id:
                    runtime_location = str(location_entry.get("name") or "").strip() or None
                    break

        all_names_by_id = {
            str(entry.get("id") or "").strip(): str(entry.get("name") or "").strip()
            for entry in character_lookup.values()
        }
        for entity_id in runtime_state.active_character_entry_ids:
            entry_name = all_names_by_id.get(str(entity_id).strip())
            if not entry_name:
                continue
            states[str(entity_id)] = self._build_snapshot_from_entry(
                story_id=story_id,
                session_id=session_id,
                entry=character_lookup[entry_name],
                current_location=runtime_location,
            )
        return states

    def _consume_text(
        self,
        *,
        story_id: str,
        session_id: str,
        text: str,
        turn_number: Optional[int],
        states: Dict[str, EntityStateSnapshot],
        character_lookup: Dict[str, Dict[str, Any]],
        location_lookup: Dict[str, Dict[str, Any]],
    ) -> None:
        """消费单段文本并更新实体状态集合。"""
        normalized_text = str(text or "").strip()
        if not normalized_text:
            return

        mentioned_characters = [
            entry
            for name, entry in character_lookup.items()
            if name and name in normalized_text
        ]
        if not mentioned_characters:
            return

        mentioned_locations = [
            name
            for name in location_lookup.keys()
            if name and name in normalized_text
        ]
        primary_location = mentioned_locations[-1] if mentioned_locations else None
        mentioned_ids = [str(entry.get("id") or "").strip() for entry in mentioned_characters]
        companions_by_entity = {
            entity_id: [other_id for other_id in mentioned_ids if other_id and other_id != entity_id]
            for entity_id in mentioned_ids
            if entity_id
        }

        for entry in mentioned_characters:
            entry_id = str(entry.get("id") or "").strip()
            if not entry_id:
                continue
            state = states.get(entry_id)
            if state is None:
                state = self._build_snapshot_from_entry(
                    story_id=story_id,
                    session_id=session_id,
                    entry=entry,
                    current_location=None,
                )
                states[entry_id] = state

            state.last_source_turn = turn_number
            state.updated_at = datetime.now()
            self._append_unique(state.evidence, normalized_text[:240], limit=4)

            if primary_location:
                state.current_location = primary_location

            for status_tag, keywords in _STATUS_KEYWORDS.items():
                if any(keyword in normalized_text for keyword in keywords):
                    self._append_unique(state.status_tags, status_tag)

            inventory_add = self._extract_inventory_changes(
                normalized_text,
                display_name=state.display_name,
                patterns=_INVENTORY_ADD_PATTERNS,
            )
            for item in inventory_add:
                self._append_unique(state.inventory, item)

            inventory_remove = self._extract_inventory_changes(
                normalized_text,
                display_name=state.display_name,
                patterns=_INVENTORY_REMOVE_PATTERNS,
            )
            if inventory_remove:
                state.inventory = [item for item in state.inventory if item not in set(inventory_remove)]

            if companions_by_entity.get(entry_id):
                state.companions = sorted(
                    set(state.companions).union(companions_by_entity[entry_id])
                )

            goal = self._extract_goal(normalized_text, display_name=state.display_name)
            if goal:
                state.short_goal = goal

            summary_bits = []
            if state.current_location:
                summary_bits.append(f"地点={state.current_location}")
            if state.status_tags:
                summary_bits.append(f"状态={','.join(state.status_tags[:4])}")
            if state.inventory:
                summary_bits.append(f"携带物={','.join(state.inventory[:4])}")
            if summary_bits:
                state.state_summary = "；".join(summary_bits)

    def _finalize_rebuild(
        self,
        *,
        story_id: str,
        session_id: str,
        states: Dict[str, EntityStateSnapshot],
        persist: bool,
        source: str,
        operation_id: Optional[str],
        sequence_start: int,
    ) -> EntityStateRebuildResponse:
        """完成重建收尾：生成变更事件、可选持久化并返回结果对象。"""
        previous_states = self.repository.list_by_story_id(story_id)
        previous_by_id = {state.entity_id: state for state in previous_states}
        normalized_states = sorted(states.values(), key=lambda item: item.display_name)
        warnings: List[str] = []
        memory_updates: List[Dict[str, Any]] = []

        for state in normalized_states:
            before_state = previous_by_id.get(state.entity_id)
            action = "rebuilt" if before_state else "created"
            memory_updates.append(
                build_memory_update_event(
                    session_id=session_id,
                    memory_layer="entity_state",
                    action=action,
                    source=source,
                    source_turn=state.last_source_turn,
                    memory_key=state.entity_id,
                    title=f"实体状态已{'重建' if action == 'rebuilt' else '建立'}: {state.display_name}",
                    before=self._snapshot_preview(before_state),
                    after=self._snapshot_preview(state),
                )
            )

        removed_entity_ids = sorted(set(previous_by_id.keys()) - set(states.keys()))
        for entity_id in removed_entity_ids:
            removed_state = previous_by_id[entity_id]
            memory_updates.append(
                build_memory_update_event(
                    session_id=session_id,
                    memory_layer="entity_state",
                    action="reset",
                    source=source,
                    source_turn=removed_state.last_source_turn,
                    memory_key=entity_id,
                    title=f"实体状态已重置: {removed_state.display_name}",
                    before=self._snapshot_preview(removed_state),
                    reason="实体在最新故事/消息重建中未再出现",
                )
            )

        if persist:
            self.repository.replace_story_states(
                story_id=story_id,
                session_id=session_id,
                states=normalized_states,
            )
            persist_memory_update_events(
                memory_updates,
                operation_id=operation_id,
                sequence_start=sequence_start,
            )

        return EntityStateRebuildResponse(
            story_id=story_id,
            session_id=session_id,
            rebuilt=True,
            entity_count=len(normalized_states),
            memory_updates=memory_updates,
            warnings=warnings,
            items=normalized_states,
        )

    def _build_snapshot_from_entry(
        self,
        *,
        story_id: str,
        session_id: str,
        entry: Dict[str, Any],
        current_location: Optional[str],
    ) -> EntityStateSnapshot:
        """从 lorebook 条目创建初始实体快照。"""
        metadata = dict(entry.get("metadata") or {})
        return EntityStateSnapshot(
            story_id=story_id,
            session_id=session_id,
            entity_id=str(entry.get("id") or "").strip(),
            entity_type="character",
            display_name=str(entry.get("name") or "").strip() or "未命名角色",
            current_location=current_location or self._extract_default_location(metadata),
            inventory=list(metadata.get("inventory") or []),
            state_summary=None,
            metadata={"source": "lorebook_seed"},
        )

    @staticmethod
    def _extract_default_location(metadata: Dict[str, Any]) -> Optional[str]:
        """读取条目元数据中的默认地点。"""
        raw = metadata.get("current_location")
        text = str(raw or "").strip()
        return text or None

    @staticmethod
    def _append_unique(items: List[str], value: Optional[str], *, limit: Optional[int] = None) -> None:
        """向列表追加去重值，并按 limit 保留尾部元素。"""
        normalized = str(value or "").strip()
        if not normalized:
            return
        if normalized not in items:
            items.append(normalized)
        if limit is not None and len(items) > limit:
            del items[:-limit]

    @staticmethod
    def _clean_inventory_item(raw: str) -> Optional[str]:
        """清洗物品片段并裁剪为短词条。"""
        value = str(raw or "").strip(" ，。；！？、\n\t")
        if not value:
            return None
        value = re.split(r"(?:，|。|；|！|？|\s|和)", value, maxsplit=1)[0].strip()
        if len(value) > 20:
            return None
        return value or None

    @staticmethod
    def _compile_entity_pattern(pattern: str, *, display_name: str) -> Optional[re.Pattern[str]]:
        """将模板正则中的 `{name}` 渲染为实体名并编译。"""
        escaped_name = re.escape(display_name)
        rendered_pattern = pattern.replace("{name}", escaped_name)
        try:
            return re.compile(rendered_pattern)
        except re.error as exc:
            logger.warning(
                "Failed to compile entity-state regex pattern for %s: %s; pattern=%s",
                display_name,
                exc,
                rendered_pattern,
            )
            return None

    def _extract_inventory_changes(
        self,
        text: str,
        *,
        display_name: str,
        patterns: Sequence[str],
    ) -> List[str]:
        """按给定规则提取携带物增减候选项。"""
        results: List[str] = []
        for pattern in patterns:
            compiled = self._compile_entity_pattern(pattern, display_name=display_name)
            if compiled is None:
                continue
            for match in compiled.findall(text):
                item = self._clean_inventory_item(match)
                if item:
                    self._append_unique(results, item)
        return results

    def _extract_goal(self, text: str, *, display_name: str) -> Optional[str]:
        """提取实体短期目标短语。"""
        for pattern in _GOAL_PATTERNS:
            compiled = self._compile_entity_pattern(pattern, display_name=display_name)
            if compiled is None:
                continue
            match = compiled.search(text)
            if not match:
                continue
            goal = str(match.group(1) or "").strip(" ，。；！？、\n\t")
            if 2 <= len(goal) <= 24:
                return goal
        return None

    @staticmethod
    def _snapshot_preview(state: Optional[EntityStateSnapshot]) -> Optional[Dict[str, Any]]:
        """生成用于 memory_update 的轻量状态快照。"""
        if state is None:
            return None
        return {
            "display_name": state.display_name,
            "current_location": state.current_location,
            "inventory": list(state.inventory)[:6],
            "status_tags": list(state.status_tags)[:6],
            "companions": list(state.companions)[:6],
            "short_goal": state.short_goal,
            "last_source_turn": state.last_source_turn,
        }
