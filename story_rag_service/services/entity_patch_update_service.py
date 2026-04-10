"""实体 patch 生成后更新编排服务。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from application.memory import build_memory_update_event, persist_memory_update_events
from models.entity_state import EntityStateCollection
from models.entity_state_event import EntityPatchExtractionResult
from services.entity_state_manager import EntityStateManager

logger = logging.getLogger(__name__)


class EntityPatchUpdateService:
    """编排实体 patch 的抽取、校验、应用、持久化与回退。"""

    def __init__(
        self,
        *,
        lorebook_manager,
        entity_state_manager: EntityStateManager,
        entity_state_fallback_service=None,
        entity_state_event_repository,
        entity_patch_extractor,
        entity_patch_validator,
        entity_patch_applier,
    ):
        self.lorebook_manager = lorebook_manager
        self.entity_state_manager = entity_state_manager
        self.entity_state_fallback_service = entity_state_fallback_service
        self.entity_state_event_repository = entity_state_event_repository
        self.entity_patch_extractor = entity_patch_extractor
        self.entity_patch_validator = entity_patch_validator
        self.entity_patch_applier = entity_patch_applier

    async def process_async(
        self,
        *,
        request,
        world_id: Optional[str],
        generated_text: str,
        llm: Any,
        source: str,
        operation_id: Optional[str],
        sequence_start: int,
        activation_logs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        current_states, character_lookup, location_lookup = self._prepare_inputs(
            request=request,
            world_id=world_id,
        )
        try:
            extraction = await self.entity_patch_extractor.extract_async(
                llm=llm,
                user_input=request.user_input,
                generated_text=generated_text,
                current_states=current_states,
            )
            return self._finalize_patch_result(
                request=request,
                world_id=world_id,
                current_states=current_states,
                character_lookup=character_lookup,
                location_lookup=location_lookup,
                extraction=extraction,
                source=source,
                operation_id=operation_id,
                sequence_start=sequence_start,
                activation_logs=activation_logs,
            )
        except Exception as exc:
            logger.warning("Entity patch async update failed, fallback to rebuild: %s", exc)
            activation_logs.append(
                {
                    "source": "entity_patch",
                    "event": "extract_failed",
                    "reason": str(exc),
                }
            )
            return self._fallback_rebuild_result(
                request=request,
                world_id=world_id,
                source=source,
                operation_id=operation_id,
                sequence_start=sequence_start,
                activation_logs=activation_logs,
                warnings=[f"entity_patch async update failed: {exc}"],
            )

    def process_sync(
        self,
        *,
        request,
        world_id: Optional[str],
        generated_text: str,
        llm: Any,
        source: str,
        operation_id: Optional[str],
        sequence_start: int,
        activation_logs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        current_states, character_lookup, location_lookup = self._prepare_inputs(
            request=request,
            world_id=world_id,
        )
        try:
            extraction = self.entity_patch_extractor.extract_sync(
                llm=llm,
                user_input=request.user_input,
                generated_text=generated_text,
                current_states=current_states,
            )
            return self._finalize_patch_result(
                request=request,
                world_id=world_id,
                current_states=current_states,
                character_lookup=character_lookup,
                location_lookup=location_lookup,
                extraction=extraction,
                source=source,
                operation_id=operation_id,
                sequence_start=sequence_start,
                activation_logs=activation_logs,
            )
        except Exception as exc:
            logger.warning("Entity patch sync update failed, fallback to rebuild: %s", exc)
            activation_logs.append(
                {
                    "source": "entity_patch",
                    "event": "extract_failed",
                    "reason": str(exc),
                }
            )
            return self._fallback_rebuild_result(
                request=request,
                world_id=world_id,
                source=source,
                operation_id=operation_id,
                sequence_start=sequence_start,
                activation_logs=activation_logs,
                warnings=[f"entity_patch sync update failed: {exc}"],
            )

    def _prepare_inputs(self, *, request, world_id: Optional[str]):
        story_id = self._resolve_story_id(request)
        current_states = self.entity_state_manager.list_story_states(story_id) if story_id else []
        entries = self._load_world_entries(world_id)
        character_lookup = self.entity_state_manager._build_character_lookup(entries)
        location_lookup = self.entity_state_manager._build_location_lookup(entries)
        return current_states, character_lookup, location_lookup

    def _finalize_patch_result(
        self,
        *,
        request,
        world_id: Optional[str],
        current_states,
        character_lookup,
        location_lookup,
        extraction: EntityPatchExtractionResult,
        source: str,
        operation_id: Optional[str],
        sequence_start: int,
        activation_logs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        story_id = self._resolve_story_id(request)
        if not story_id:
            return {
                "entity_state_snapshot": None,
                "entity_state_updates": [],
                "world_update": None,
                "memory_updates": [],
                "warnings": ["missing_story_id"],
                "used_fallback_rebuild": False,
            }

        validated = self.entity_patch_validator.validate(
            extraction=extraction,
            character_lookup=character_lookup,
            location_lookup=location_lookup,
        )

        if not validated.patches and validated.warnings:
            return self._fallback_rebuild_result(
                request=request,
                world_id=world_id,
                source=source,
                operation_id=operation_id,
                sequence_start=sequence_start,
                activation_logs=activation_logs,
                warnings=validated.warnings,
            )

        if not validated.patches:
            snapshot = EntityStateCollection(
                story_id=story_id,
                session_id=request.session_id,
                items=current_states,
                total=len(current_states),
            ).model_dump(mode="json")
            return {
                "entity_state_snapshot": snapshot,
                "entity_state_updates": [],
                "world_update": {
                    "entity_patch": {
                        "patch_count": 0,
                        "warnings": validated.warnings,
                        "fallback_used": False,
                    }
                },
                "memory_updates": [],
                "warnings": validated.warnings,
                "used_fallback_rebuild": False,
            }

        apply_result = self.entity_patch_applier.apply(
            story_id=story_id,
            session_id=request.session_id,
            current_states=current_states,
            patches=validated.patches,
            source=source,
            operation_id=operation_id,
            sequence_start=sequence_start,
        )
        self.entity_state_event_repository.append_events(apply_result.events)
        self.entity_state_manager.repository.replace_story_states(
            story_id=story_id,
            session_id=request.session_id,
            states=apply_result.snapshots,
        )

        memory_updates = [
            build_memory_update_event(
                session_id=request.session_id,
                memory_layer="entity_state",
                action="patched",
                source=source,
                source_turn=event.source_turn,
                memory_key=f"{event.entity_id}:{event.field_name}",
                title=f"实体状态字段已更新: {(event.entity_name or event.entity_id)}.{event.field_name}",
                before={"field": event.field_name, "value": event.before},
                after={"field": event.field_name, "value": event.after},
                reason=event.evidence_text,
            )
            for event in apply_result.events
        ]
        persist_memory_update_events(
            memory_updates,
            operation_id=operation_id,
            sequence_start=sequence_start,
        )

        activation_logs.append(
            {
                "source": "entity_patch",
                "event": "applied",
                "patch_count": len(validated.patches),
                "warning_count": len(validated.warnings),
            }
        )

        snapshot = EntityStateCollection(
            story_id=story_id,
            session_id=request.session_id,
            items=apply_result.snapshots,
            total=len(apply_result.snapshots),
        ).model_dump(mode="json")
        return {
            "entity_state_snapshot": snapshot,
            "entity_state_updates": [event.model_dump(mode="json") for event in apply_result.events],
            "world_update": {
                "entity_patch": {
                    "patch_count": len(validated.patches),
                    "warnings": validated.warnings,
                    "fallback_used": False,
                }
            },
            "memory_updates": memory_updates,
            "warnings": validated.warnings,
            "used_fallback_rebuild": False,
        }

    def _fallback_rebuild_result(
        self,
        *,
        request,
        world_id: Optional[str],
        source: str,
        operation_id: Optional[str],
        sequence_start: int,
        activation_logs: List[Dict[str, Any]],
        warnings: List[str],
    ) -> Dict[str, Any]:
        activation_logs.append(
            {
                "source": "entity_patch",
                "event": "fallback_rebuild",
                "warnings": list(warnings)[:4],
            }
        )
        story_id = self._resolve_story_id(request)
        if not story_id:
            return {
                "entity_state_snapshot": None,
                "entity_state_updates": [],
                "world_update": {
                    "entity_patch": {
                        "patch_count": 0,
                        "warnings": warnings,
                        "fallback_used": True,
                    }
                },
                "memory_updates": [],
                "warnings": warnings,
                "used_fallback_rebuild": True,
            }

        rebuild_result = (
            self.entity_state_fallback_service.rebuild_session_state(
                session_id=request.session_id,
                story_id=story_id,
                world_id=world_id,
                messages=request.context.messages if request.context else [],
                source=source,
                operation_id=operation_id,
                sequence_start=sequence_start,
                activation_logs=activation_logs,
            )
            if self.entity_state_fallback_service is not None
            else self.entity_state_manager.rebuild_session_state(
                session_id=request.session_id,
                story_id=story_id,
                world_id=world_id,
                messages=request.context.messages if request.context else [],
                persist=True,
                source=source,
                operation_id=operation_id,
                sequence_start=sequence_start,
            )
        )
        snapshot = EntityStateCollection(
            story_id=story_id,
            session_id=request.session_id,
            items=rebuild_result.items,
            total=len(rebuild_result.items),
        ).model_dump(mode="json") if rebuild_result.rebuilt else None
        return {
            "entity_state_snapshot": snapshot,
            "entity_state_updates": [],
            "world_update": {
                "entity_patch": {
                    "patch_count": 0,
                    "warnings": warnings,
                    "fallback_used": True,
                }
            },
            "memory_updates": list(rebuild_result.memory_updates or []),
            "warnings": warnings,
            "used_fallback_rebuild": True,
        }

    def _load_world_entries(self, world_id: Optional[str]) -> List[Dict[str, Any]]:
        if not self.lorebook_manager:
            return []
        try:
            return list(self.lorebook_manager.get_all_entries(world_id=world_id))
        except Exception:
            return []

    @staticmethod
    def _resolve_story_id(request) -> Optional[str]:
        story_id = getattr(request, "story_id", None)
        if story_id:
            return str(story_id).strip() or None
        session_id = str(getattr(request, "session_id", "") or "").strip()
        prefix = "story-"
        suffix = "-v2"
        if session_id.startswith(prefix) and session_id.endswith(suffix):
            return session_id[len(prefix):-len(suffix)] or None
        return None
