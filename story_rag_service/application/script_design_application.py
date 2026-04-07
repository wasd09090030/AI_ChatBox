"""剧本设计管理应用服务。"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from models.script_design import (
    ScriptDesign,
    ScriptDesignCreate,
    ScriptDesignStatus,
    ScriptDesignUpdate,
)
from repositories.script_design_repository import ScriptDesignRepository
from services.story_manager import StoryManager
from services.world_manager import WorldManager


class ScriptDesignApplicationService:
    """剧本设计应用服务。

    负责剧本设计的生命周期管理，并处理与世界、故事绑定关系的业务约束。
    """

    def __init__(
        self,
        script_design_repository: ScriptDesignRepository,
        world_manager: WorldManager,
        story_manager: StoryManager,
    ):
        """初始化剧本设计应用服务依赖。"""
        self.script_design_repository = script_design_repository
        self.world_manager = world_manager
        self.story_manager = story_manager

    def list_script_designs(
        self,
        world_id: Optional[str] = None,
        status: Optional[ScriptDesignStatus] = None,
    ) -> List[ScriptDesign]:
        """按可选 world/status 过滤列出剧本设计。"""
        return self.script_design_repository.list_all(world_id=world_id, status=status)

    def create_script_design(self, data: ScriptDesignCreate) -> ScriptDesign:
        """创建剧本设计并执行结构规范化校验。"""
        self._ensure_world_exists(data.world_id)
        script_design = ScriptDesign(**data.model_dump())
        normalized = self._normalize_and_validate(script_design)
        return self.script_design_repository.save(normalized)

    def get_script_design(self, script_design_id: str) -> Optional[ScriptDesign]:
        """按 id 获取剧本设计。"""
        return self.script_design_repository.get(script_design_id)

    def update_script_design(self, script_design_id: str, data: ScriptDesignUpdate) -> Optional[ScriptDesign]:
        """更新剧本设计并自动递增版本号。"""
        existing = self.script_design_repository.get(script_design_id)
        if existing is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        merged_data = existing.model_dump(mode="python")
        merged_data.update(update_data)
        merged_data["version"] = existing.version + 1
        merged_data["updated_at"] = datetime.now()
        normalized = self._normalize_and_validate(ScriptDesign(**merged_data))
        return self.script_design_repository.save(normalized)

    def delete_script_design(self, script_design_id: str) -> Optional[dict]:
        """删除剧本设计。

        若仍有故事绑定，则返回阻断信息而不执行删除。
        """
        existing = self.script_design_repository.get(script_design_id)
        if existing is None:
            return None

        bindings = self.list_story_bindings(script_design_id)
        if bindings:
            return {
                "deleted": False,
                "blocked": True,
                "story_binding_count": len(bindings),
                "script_design_id": script_design_id,
            }

        deleted = self.script_design_repository.delete(script_design_id)
        return {
            "deleted": deleted,
            "blocked": False,
            "story_binding_count": 0,
            "script_design_id": script_design_id,
        }

    def delete_script_designs_by_world(self, world_id: str) -> int:
        """按 world_id 批量删除剧本设计。"""
        return self.script_design_repository.delete_by_world(world_id)

    def list_story_bindings(self, script_design_id: str) -> List[dict]:
        """列出与指定剧本设计绑定的故事摘要信息。"""
        stories = self.story_manager.list_stories()
        bindings = []
        for story in stories:
            bound_id = story.metadata.get("script_design_id") if story.metadata else None
            if bound_id != script_design_id:
                continue
            bindings.append(
                {
                    "story_id": story.id,
                    "title": story.title,
                    "world_id": story.world_id,
                    "world_name": story.world_name,
                    "updated_at": story.updated_at,
                }
            )
        return bindings

    def _ensure_world_exists(self, world_id: str) -> None:
        """确保 world_id 有效，不存在则抛出异常。"""
        if not self.world_manager.world_exists(world_id):
            raise ValueError("World not found")

    def _normalize_and_validate(self, script_design: ScriptDesign) -> ScriptDesign:
        """规范化并校验剧本设计结构完整性。"""
        stage_ids = set()
        for index, stage in enumerate(sorted(script_design.stage_outlines, key=lambda item: item.order)):
            stage.order = index
            if stage.id in stage_ids:
                raise ValueError(f"Duplicate stage id: {stage.id}")
            stage_ids.add(stage.id)

        event_ids = set()
        foreshadow_ids = {item.id for item in script_design.foreshadows}
        for index, event in enumerate(sorted(script_design.event_nodes, key=lambda item: (item.stage_id, item.order))):
            if event.stage_id not in stage_ids:
                raise ValueError(f"Event references unknown stage: {event.stage_id}")
            if event.id in event_ids:
                raise ValueError(f"Duplicate event id: {event.id}")
            event_ids.add(event.id)
            event.order = index if event.stage_id else event.order

        for event in script_design.event_nodes:
            missing_prereqs = [item for item in event.prerequisite_event_ids if item not in event_ids]
            if missing_prereqs:
                raise ValueError(f"Event references unknown prerequisite ids: {', '.join(missing_prereqs)}")
            missing_unlocks = [item for item in event.unlocks_event_ids if item not in event_ids]
            if missing_unlocks:
                raise ValueError(f"Event references unknown unlock ids: {', '.join(missing_unlocks)}")
            missing_foreshadows = [item for item in event.foreshadow_ids if item not in foreshadow_ids]
            if missing_foreshadows:
                raise ValueError(f"Event references unknown foreshadow ids: {', '.join(missing_foreshadows)}")

        for foreshadow in script_design.foreshadows:
            if foreshadow.planted_stage_id and foreshadow.planted_stage_id not in stage_ids:
                raise ValueError(f"Foreshadow references unknown planted stage: {foreshadow.planted_stage_id}")
            if foreshadow.expected_payoff_stage_id and foreshadow.expected_payoff_stage_id not in stage_ids:
                raise ValueError(
                    f"Foreshadow references unknown payoff stage: {foreshadow.expected_payoff_stage_id}"
                )
            if foreshadow.planted_event_id and foreshadow.planted_event_id not in event_ids:
                raise ValueError(f"Foreshadow references unknown planted event: {foreshadow.planted_event_id}")
            if foreshadow.expected_payoff_event_id and foreshadow.expected_payoff_event_id not in event_ids:
                raise ValueError(
                    f"Foreshadow references unknown payoff event: {foreshadow.expected_payoff_event_id}"
                )

        script_design.stage_outlines = sorted(script_design.stage_outlines, key=lambda item: item.order)
        stage_order_map = {stage.id: index for index, stage in enumerate(script_design.stage_outlines)}
        script_design.event_nodes = sorted(
            script_design.event_nodes,
            key=lambda item: (stage_order_map.get(item.stage_id, 0), item.order, item.title),
        )

        stage_event_counters = {stage_id: 0 for stage_id in stage_ids}
        for event in script_design.event_nodes:
            event.order = stage_event_counters[event.stage_id]
            stage_event_counters[event.stage_id] += 1

        script_design.updated_at = datetime.now()
        return script_design