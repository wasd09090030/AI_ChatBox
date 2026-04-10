from __future__ import annotations

from typing import Any, Dict, List, Optional

from application.story_generation_common import load_world_config, retrieve_rag_context
from config import settings
from models.story import StoryContext, StoryGenerationRequest

from .models import MemoryBundle, MemoryOrchestratorResult
from .providers import build_dialogue_controls, load_profile_snapshot, load_script_guidance


class MemoryOrchestrator:
    def __init__(
        self,
        *,
        lorebook_manager,
        history_manager,
        world_manager=None,
        roleplay_manager=None,
        script_design_app=None,
        summary_memory_manager=None,
        story_runtime_manager=None,
        entity_state_event_replay_service=None,
        recent_message_count: int = 5,
    ):
        self.lorebook_manager = lorebook_manager
        self.history_manager = history_manager
        self.world_manager = world_manager
        self.roleplay_manager = roleplay_manager
        self.script_design_app = script_design_app
        self.summary_memory_manager = summary_memory_manager
        self.story_runtime_manager = story_runtime_manager
        self.entity_state_event_replay_service = entity_state_event_replay_service
        self.recent_message_count = recent_message_count

    def build_bundle(
        self,
        *,
        request: StoryGenerationRequest,
        context: StoryContext,
        history_k: int = 5,
        history_score_threshold: Optional[float] = None,
        assistant_weight: Optional[float] = None,
        log_prefix: str = "",
    ) -> MemoryOrchestratorResult:
        retrieved_contexts, retrieved_history, world_id, activation_logs = retrieve_rag_context(
            request=request,
            context=context,
            lorebook_manager=self.lorebook_manager,
            history_manager=self.history_manager,
            recent_message_count=self.recent_message_count,
            history_k=history_k,
            history_score_threshold=history_score_threshold,
            assistant_weight=assistant_weight,
            log_prefix=log_prefix,
        )

        world_config = load_world_config(self.world_manager, world_id, log_prefix=log_prefix)
        profile_snapshot = self._load_profile_snapshot(request)
        dialogue_controls = self._build_dialogue_controls(request)
        summary_memory = self._load_summary_memory(request.session_id, activation_logs)
        script_guidance = self._load_script_guidance(request, activation_logs)
        story_id = self._resolve_story_id(request.session_id, getattr(request, "story_id", None))
        runtime_snapshot = self._load_runtime_snapshot(story_id, activation_logs)
        entity_memory = self._load_entity_memory(
            story_id=story_id,
            session_id=request.session_id,
            activation_logs=activation_logs,
        )

        bundle: MemoryBundle = {
            "episodic": {
                "recent_messages": [
                    {
                        "role": message.role,
                        "content": message.content,
                    }
                    for message in context.messages[-(self.recent_message_count * 2) :]
                ],
                "recalled_episodes": list(retrieved_history or []),
            },
            "semantic": {
                "summary_text": (summary_memory or {}).get("summary_text", ""),
                "key_facts": list((summary_memory or {}).get("key_facts") or []),
                "entities": dict((summary_memory or {}).get("entities") or {}),
                "raw_record": summary_memory,
            },
            "profile": {
                "persona": (profile_snapshot or {}).get("persona"),
                "character_card": (profile_snapshot or {}).get("character_card"),
                "story_state": (profile_snapshot or {}).get("story_state"),
                "raw_profile": profile_snapshot or {},
            },
            "procedural": {
                "authors_note": getattr(request, "authors_note", None),
                "dialogue_controls": dict(dialogue_controls or {}),
                "script_guidance": dict(script_guidance or {}),
                "mode": getattr(request, "mode", "narrative") or "narrative",
                "instruction": getattr(request, "instruction", None),
                "focus_instruction": getattr(request, "focus_instruction", None),
                "focus_label": getattr(request, "focus_label", None),
                "script_design_context": script_guidance or {},
            },
            "world": {
                "world_id": world_id,
                "retrieved_lore": list(retrieved_contexts or []),
                "world_config": world_config or {},
            },
            "runtime": {
                "story_id": story_id,
                "runtime_state_id": (runtime_snapshot or {}).get("id"),
                "current_stage_id": (runtime_snapshot or {}).get("current_stage_id"),
                "current_event_id": (runtime_snapshot or {}).get("current_event_id"),
                "creation_mode": (runtime_snapshot or {}).get("creation_mode"),
                "raw_record": runtime_snapshot,
            },
            "entity": {
                "story_id": story_id,
                "entity_type": "character",
                "tracked_entities": int((entity_memory or {}).get("total") or 0),
                "entity_state_snapshot": entity_memory,
                "recent_entity_updates": list((entity_memory or {}).get("recent_entity_updates") or []),
                "raw_record": entity_memory,
            },
            "meta": {
                "session_id": request.session_id,
                "activation_logs": activation_logs,
            },
        }
        return {
            "bundle": bundle,
            "world_id": world_id,
            "activation_logs": activation_logs,
        }

    def _load_profile_snapshot(self, request: StoryGenerationRequest) -> Dict[str, Any]:
        try:
            return load_profile_snapshot(self.roleplay_manager, request)
        except Exception:
            return {}

    @staticmethod
    def _build_dialogue_controls(request: StoryGenerationRequest) -> Dict[str, Any]:
        return build_dialogue_controls(request)

    def _load_script_guidance(
        self,
        request: StoryGenerationRequest,
        activation_logs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        try:
            script_guidance = load_script_guidance(self.script_design_app, request)
        except Exception:
            return {}

        if script_guidance:
            activation_logs.append(
                {
                    "source": "script_design",
                    "event": "applied",
                    "script_design_id": script_guidance.get("script_design_id"),
                    "script_title": script_guidance.get("title"),
                    "active_stage": (script_guidance.get("active_stage") or {}).get("title"),
                    "active_event": (script_guidance.get("active_event") or {}).get("title"),
                }
            )
        return script_guidance

    def _load_summary_memory(
        self,
        session_id: str,
        activation_logs: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not self.summary_memory_manager or not settings.rp_summary_memory_enabled:
            return None

        summary_memory = self.summary_memory_manager.get_summary(session_id)
        if summary_memory:
            activation_logs.append(
                {
                    "source": "summary_memory",
                    "event": "applied",
                    "last_turn": summary_memory.get("last_turn"),
                    "facts_count": len(summary_memory.get("key_facts") or []),
                }
            )
        return summary_memory

    def _resolve_story_id(
        self,
        session_id: str,
        explicit_story_id: Optional[str],
    ) -> Optional[str]:
        if explicit_story_id:
            return str(explicit_story_id)
        if self.story_runtime_manager:
            return self.story_runtime_manager.derive_story_id(session_id)
        return None

    def _load_runtime_snapshot(
        self,
        story_id: Optional[str],
        activation_logs: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not story_id or not self.story_runtime_manager:
            return None
        runtime_state = self.story_runtime_manager.get_runtime_state(story_id)
        if runtime_state:
            activation_logs.append(
                {
                    "source": "story_runtime",
                    "event": "applied",
                    "runtime_state_id": runtime_state.id,
                    "current_stage_id": runtime_state.current_stage_id,
                    "current_event_id": runtime_state.current_event_id,
                }
            )
            return runtime_state.model_dump(mode="json")
        return None

    def _load_entity_memory(
        self,
        *,
        story_id: Optional[str],
        session_id: str,
        activation_logs: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not story_id or not self.entity_state_event_replay_service:
            return None
        replay_result = self.entity_state_event_replay_service.replay_story_state(
            story_id=story_id,
            session_id=session_id,
            source="story_memory_read",
            allow_empty_result=True,
            persist=False,
        )
        snapshot = {
            "story_id": story_id,
            "session_id": session_id,
            "entity_type": "character",
            "items": [item.model_dump(mode="json") for item in replay_result.items],
            "total": len(replay_result.items),
            "recent_entity_updates": list(replay_result.memory_updates or [])[-10:],
        }
        if replay_result.items:
            activation_logs.append(
                {
                    "source": "entity_memory",
                    "event": "applied",
                    "tracked_entities": len(replay_result.items),
                }
            )
        return snapshot
