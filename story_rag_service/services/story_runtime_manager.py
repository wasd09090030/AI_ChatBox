"""
Runtime state manager for dual-mode story creation.
"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

from models.script_design import ScriptDesign, ScriptEventNode, ScriptStage
from models.stored_story import StoredStory
from models.story_runtime import (
    ProgressIntent,
    ScriptConsistencyCheckResult,
    ScriptRoundContract,
    ScriptRuntimeState,
    ScriptRuntimeStateUpdate,
)
from repositories.story_runtime_repository import SqliteStoryRuntimeRepository

# 变量作用：模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)


class StoryRuntimeManager:
    """管理故事运行时状态与剧本推进约束。

    该管理器负责：
    1. 初始化/恢复运行时状态；
    2. 基于剧本设计生成本轮约束合同；
    3. 对生成结果做一致性校验并决定是否推进状态；
    4. 将运行时进度同步回故事元数据。
    """

    def __init__(
        self,
        repository: SqliteStoryRuntimeRepository,
        script_design_app,
        story_manager,
    ):
        """注入运行时状态仓储与上层应用服务。"""
        self.repository = repository
        self.script_design_app = script_design_app
        self.story_manager = story_manager

    @staticmethod
    def derive_story_id(session_id: Optional[str]) -> Optional[str]:
        """从 `story-<id>-v2` 形式的会话 ID 还原 story_id。"""
        text = str(session_id or "").strip()
        if text.startswith("story-") and text.endswith("-v2"):
            return text[len("story-"):-len("-v2")]
        return None

    def get_runtime_state(self, story_id: str) -> Optional[ScriptRuntimeState]:
        """按 story_id 读取运行时状态。"""
        return self.repository.get_by_story_id(story_id)

    def save_runtime_state(self, runtime_state: ScriptRuntimeState) -> ScriptRuntimeState:
        """持久化运行时状态，并刷新 `updated_at`。"""
        runtime_state.updated_at = datetime.now()
        return self.repository.save(runtime_state)

    def update_runtime_state(
        self,
        story_id: str,
        update: ScriptRuntimeStateUpdate,
    ) -> Optional[ScriptRuntimeState]:
        """增量更新运行时状态。

        当 `script_design_id` 发生变化时，会重置事件推进与伏笔兑现相关字段，
        以避免旧剧本状态污染新剧本。
        """
        state = self.get_runtime_state(story_id)
        if state is None:
            return None

        update_data = update.model_dump(exclude_unset=True)
        script_design_id = update_data.pop("script_design_id", None)

        if script_design_id is not None and script_design_id != state.script_design_id:
            script_design = self.script_design_app.get_script_design(script_design_id)
            if script_design is None:
                raise ValueError("Script design not found")

            preferred_stage_id = update_data.get("current_stage_id") or state.current_stage_id
            preferred_event_id = update_data.get("current_event_id") or state.current_event_id
            stage = self._resolve_stage(script_design, preferred_stage_id)
            event = self._resolve_event(script_design, stage, preferred_event_id)

            state.script_design_id = script_design_id
            state.current_stage_id = stage.id if stage else None
            state.current_event_id = event.id if event else None
            state.completed_event_ids = []
            state.skipped_event_ids = []
            state.active_foreshadow_ids = [
                item.id for item in script_design.foreshadows if item.status != "paid_off"
            ]
            state.paid_off_foreshadow_ids = []
            state.abandoned_foreshadow_ids = []

        for key, value in update_data.items():
            setattr(state, key, value)
        state.updated_at = datetime.now()
        return self.repository.save(state)

    def ensure_runtime_state(
        self,
        *,
        story_id: str,
        session_id: str,
        world_id: Optional[str],
        script_design_id: str,
        creation_mode: str,
        preferred_stage_id: Optional[str] = None,
        preferred_event_id: Optional[str] = None,
    ) -> ScriptRuntimeState:
        """确保 story 对应的运行时状态存在。

        若已存在，则按入参修正关键字段；若不存在，则基于剧本设计创建初始状态。
        """
        existing = self.repository.get_by_story_id(story_id)
        if existing is not None:
            changed = False
            if existing.script_design_id != script_design_id:
                existing.script_design_id = script_design_id
                changed = True
            if existing.session_id != session_id:
                existing.session_id = session_id
                changed = True
            if existing.world_id != world_id:
                existing.world_id = world_id
                changed = True
            if existing.creation_mode != creation_mode:
                existing.creation_mode = creation_mode
                changed = True
            if preferred_stage_id and existing.current_stage_id != preferred_stage_id:
                existing.current_stage_id = preferred_stage_id
                changed = True
            if preferred_event_id and existing.current_event_id != preferred_event_id:
                existing.current_event_id = preferred_event_id
                changed = True
            if changed:
                return self.save_runtime_state(existing)
            return existing

        script_design = self.script_design_app.get_script_design(script_design_id)
        if script_design is None:
            raise ValueError("Script design not found")

        stage = self._resolve_stage(script_design, preferred_stage_id)
        event = self._resolve_event(script_design, stage, preferred_event_id)

        state = ScriptRuntimeState(
            story_id=story_id,
            session_id=session_id,
            world_id=world_id,
            script_design_id=script_design_id,
            creation_mode=creation_mode if creation_mode in {"improv", "scripted"} else "improv",
            current_stage_id=stage.id if stage else None,
            current_event_id=event.id if event else None,
            active_foreshadow_ids=[
                item.id for item in script_design.foreshadows if item.status != "paid_off"
            ],
        )
        return self.save_runtime_state(state)

    def restore_runtime_state(
        self,
        *,
        story: StoredStory,
        runtime_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Optional[ScriptRuntimeState]:
        """从快照或故事元数据恢复运行时状态。

        恢复优先级：
        1. 显式传入的 `runtime_snapshot`；
        2. `story.metadata.runtime_initial_snapshot`；
        3. 基于 metadata/script_design 的推导恢复；
        4. 若无法推导则返回现有状态。
        """
        existing = self.get_runtime_state(story.id)

        if runtime_snapshot:
            restored_payload = dict(runtime_snapshot)
            if existing is not None:
                restored_payload.setdefault("id", existing.id)
                restored_payload.setdefault("session_id", existing.session_id)
                restored_payload.setdefault("world_id", existing.world_id)
                restored_payload.setdefault("created_at", existing.created_at)
            restored_payload["story_id"] = story.id
            restored = ScriptRuntimeState(**restored_payload)
            return self.save_runtime_state(restored)

        metadata = dict(story.metadata or {})
        initial_snapshot = metadata.get("runtime_initial_snapshot")
        if isinstance(initial_snapshot, dict) and initial_snapshot:
            return self.restore_runtime_state(story=story, runtime_snapshot=initial_snapshot)

        script_design_id = None
        if isinstance(metadata.get("script_design_id"), str):
            script_design_id = metadata.get("script_design_id")
        elif existing is not None:
            script_design_id = existing.script_design_id

        if not script_design_id:
            return existing

        script_design = self.script_design_app.get_script_design(script_design_id)
        if script_design is None:
            raise ValueError("Script design not found")

        preferred_stage_id = None
        preferred_event_id = None
        if isinstance(initial_snapshot, dict):
            if isinstance(initial_snapshot.get("current_stage_id"), str):
                preferred_stage_id = initial_snapshot.get("current_stage_id")
            if isinstance(initial_snapshot.get("current_event_id"), str):
                preferred_event_id = initial_snapshot.get("current_event_id")

        stage = self._resolve_stage(script_design, preferred_stage_id)
        event = self._resolve_event(script_design, stage, preferred_event_id)

        restored = ScriptRuntimeState(
            story_id=story.id,
            session_id=(existing.session_id if existing is not None else f"story-{story.id}-v2"),
            world_id=story.world_id,
            script_design_id=script_design_id,
            creation_mode=(
                existing.creation_mode
                if existing is not None
                else (
                    str(metadata.get("creation_mode"))
                    if metadata.get("creation_mode") in {"improv", "scripted"}
                    else ("scripted" if metadata.get("follow_script_design") is True else "improv")
                )
            ),
            current_stage_id=stage.id if stage else None,
            current_event_id=event.id if event else None,
            active_foreshadow_ids=[
                item.id for item in script_design.foreshadows if item.status != "paid_off"
            ],
            created_at=existing.created_at if existing is not None else datetime.now(),
        )
        if existing is not None:
            restored.id = existing.id
        return self.save_runtime_state(restored)

    def build_round_contract(
        self,
        *,
        script_design: ScriptDesign,
        runtime_state: ScriptRuntimeState,
        progress_intent: ProgressIntent,
    ) -> ScriptRoundContract:
        """构建单轮生成合同（Round Contract）。

        合同用于向生成器约束本轮可用角色、地点、RAG 范围与伏笔要求，
        并附带推进意图（hold/advance/complete）。
        """
        stage = self._resolve_stage(script_design, runtime_state.current_stage_id)
        event = self._resolve_event(script_design, stage, runtime_state.current_event_id)

        allowed_character_ids: List[str] = []
        allowed_location_ids: List[str] = []
        rag_scope_entry_ids: List[str] = []
        required_foreshadow_ids: List[str] = []

        if stage:
            allowed_character_ids.extend(stage.linked_role_ids)
            rag_scope_entry_ids.extend(stage.linked_lorebook_entry_ids)
        if event:
            allowed_character_ids.extend(event.participant_role_ids)
            rag_scope_entry_ids.extend(event.participant_lorebook_entry_ids)
            required_foreshadow_ids.extend(event.foreshadow_ids)

        foreshadow_lookup = {
            item.id: item.model_dump()
            for item in script_design.foreshadows
            if item.id in set(required_foreshadow_ids + list(runtime_state.active_foreshadow_ids))
        }

        if event and event.participant_lorebook_entry_ids:
            allowed_location_ids.extend(event.participant_lorebook_entry_ids)

        completion_guard = None
        if event is not None:
            completion_guard = (
                event.expected_outcome
                or event.objective
                or f"需要明确推进或完成事件“{event.title}”"
            )

        return ScriptRoundContract(
            script_design_id=script_design.id,
            stage_id=stage.id if stage else None,
            event_id=event.id if event else None,
            stage_title=stage.title if stage else None,
            event_title=event.title if event else None,
            stage_goal=stage.goal if stage else None,
            event_objective=event.objective if event else None,
            event_obstacle=event.obstacle if event else None,
            allowed_character_ids=self._unique_list(allowed_character_ids),
            allowed_location_ids=self._unique_list(allowed_location_ids),
            required_foreshadow_ids=self._unique_list(required_foreshadow_ids),
            highlighted_foreshadows=list(foreshadow_lookup.values())[:3],
            rag_scope_entry_ids=self._unique_list(rag_scope_entry_ids),
            progress_intent=progress_intent,
            completion_guard=completion_guard,
        )

    def run_consistency_check(
        self,
        *,
        generated_text: str,
        contract: ScriptRoundContract,
    ) -> ScriptConsistencyCheckResult:
        """对生成文本做轻量一致性检查。

        当前规则偏保守：主要拦截空文本、无事件却要求推进、以及过短却要求完成。
        """
        result = ScriptConsistencyCheckResult()
        text = (generated_text or "").strip()
        if not text:
            result.passed = False
            result.event_alignment = "fail"
            result.notes.append("生成内容为空，无法用于严格剧本推进。")
            return result

        if contract.progress_intent == "complete" and len(text) < 120:
            result.passed = False
            result.event_alignment = "fail"
            result.unsupported_completion = True
            result.notes.append("本轮文本过短，不支持直接完成当前事件。")

        if contract.progress_intent in {"advance", "complete"} and not contract.event_id:
            result.passed = False
            result.event_alignment = "fail"
            result.notes.append("未解析到当前事件，不能执行结构推进。")

        if contract.progress_intent == "hold":
            result.notes.append("本轮仅描写，不自动推进剧情状态。")

        return result

    def apply_generation_result(
        self,
        *,
        runtime_state: ScriptRuntimeState,
        script_design: ScriptDesign,
        contract: ScriptRoundContract,
        check_result: ScriptConsistencyCheckResult,
        allow_state_transition: bool,
    ) -> ScriptRuntimeState:
        """将本轮生成结果映射为运行时状态变化。

        先保存合同与检查快照，再根据推进意图决定是否迁移到下一事件，
        同步已兑现伏笔，并最终持久化。
        """
        runtime_state.last_contract_snapshot = contract.model_dump(mode="python")
        runtime_state.last_check_result = check_result.model_dump(mode="python")

        if not allow_state_transition or not check_result.passed:
            return self.save_runtime_state(runtime_state)

        if contract.progress_intent == "hold" or not contract.event_id:
            return self.save_runtime_state(runtime_state)

        current_event = self._resolve_event(script_design, None, contract.event_id)
        if current_event is None:
            return self.save_runtime_state(runtime_state)

        # 推进意图 advance 表示“推进到当前合同事件”，不自动标记完成。
        if contract.progress_intent == "advance":
            runtime_state.current_stage_id = current_event.stage_id
            runtime_state.current_event_id = current_event.id
            return self.save_runtime_state(runtime_state)

        if current_event.id not in runtime_state.completed_event_ids:
            runtime_state.completed_event_ids.append(current_event.id)

        next_event = self._next_event(script_design, current_event)
        if next_event is not None:
            runtime_state.current_stage_id = next_event.stage_id
            runtime_state.current_event_id = next_event.id
        else:
            runtime_state.current_event_id = current_event.id
            runtime_state.current_stage_id = current_event.stage_id

        for foreshadow_id in contract.required_foreshadow_ids:
            if foreshadow_id in runtime_state.active_foreshadow_ids:
                runtime_state.active_foreshadow_ids.remove(foreshadow_id)
            if foreshadow_id not in runtime_state.paid_off_foreshadow_ids:
                runtime_state.paid_off_foreshadow_ids.append(foreshadow_id)

        return self.save_runtime_state(runtime_state)

    def sync_story_metadata(self, runtime_state: ScriptRuntimeState) -> None:
        """将运行时关键信息回写到故事元数据，供 UI/查询侧消费。"""
        progress_payload = {
            "script_design_id": runtime_state.script_design_id,
            "active_stage_id": runtime_state.current_stage_id,
            "active_event_id": runtime_state.current_event_id,
            "follow_script_design": runtime_state.creation_mode == "scripted",
            "creation_mode": runtime_state.creation_mode,
            "runtime_state_id": runtime_state.id,
        }
        self.story_manager.update_story_progress(runtime_state.story_id, progress_payload)  # type: ignore[arg-type]

    def _resolve_stage(
        self,
        script_design: ScriptDesign,
        preferred_stage_id: Optional[str],
    ) -> Optional[ScriptStage]:
        """解析当前阶段。

        优先级：显式 preferred_stage_id -> 默认策略 preferred_stage_id -> 首阶段。
        """
        if preferred_stage_id:
            match = next(
                (item for item in script_design.stage_outlines if item.id == preferred_stage_id),
                None,
            )
            if match is not None:
                return match

        preferred = getattr(script_design.default_generation_policy, "preferred_stage_id", None)
        if preferred:
            match = next((item for item in script_design.stage_outlines if item.id == preferred), None)
            if match is not None:
                return match

        return script_design.stage_outlines[0] if script_design.stage_outlines else None

    def _resolve_event(
        self,
        script_design: ScriptDesign,
        stage: Optional[ScriptStage],
        preferred_event_id: Optional[str],
    ) -> Optional[ScriptEventNode]:
        """解析当前事件。

        优先级：显式 preferred_event_id -> 当前阶段 pending/active -> 当前阶段首事件
        -> 全局 pending/active -> 全局首事件。
        """
        if preferred_event_id:
            match = next(
                (item for item in script_design.event_nodes if item.id == preferred_event_id),
                None,
            )
            if match is not None:
                return match

        if stage is not None:
            stage_events = [item for item in script_design.event_nodes if item.stage_id == stage.id]
            pending = next((item for item in stage_events if item.status in {"pending", "active"}), None)
            if pending is not None:
                return pending
            if stage_events:
                return stage_events[0]

        pending = next((item for item in script_design.event_nodes if item.status in {"pending", "active"}), None)
        if pending is not None:
            return pending
        return script_design.event_nodes[0] if script_design.event_nodes else None

    def _next_event(
        self,
        script_design: ScriptDesign,
        current_event: ScriptEventNode,
    ) -> Optional[ScriptEventNode]:
        """按阶段顺序+事件顺序，返回当前事件的下一个事件。"""
        stage_order = {stage.id: stage.order for stage in script_design.stage_outlines}
        ordered = sorted(
            script_design.event_nodes,
            key=lambda item: (stage_order.get(item.stage_id, 0), item.order, item.title),
        )
        current_index = next((index for index, item in enumerate(ordered) if item.id == current_event.id), -1)
        if current_index < 0:
            return None
        if current_index + 1 >= len(ordered):
            return None
        return ordered[current_index + 1]

    @staticmethod
    def _unique_list(items: List[str]) -> List[str]:
        """去空白并保持顺序去重。"""
        normalized = [str(item).strip() for item in items if str(item).strip()]
        return list(dict.fromkeys(normalized))
