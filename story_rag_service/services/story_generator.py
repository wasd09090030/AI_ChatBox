"""故事生成服务（编排层）。

定位：作为 story 生成主链路的总编排器，维持稳定对外接口。

核心职责：
1) 协调 memory bundle、prompt 构建与 LLM 调用；
2) 在生成后落盘消息、更新摘要/实体状态并产出 story_memory；
3) 同时支持异步非流式、同步、SSE 流式三种生成模式。
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from application.ports import LLMGateway
from langchain_core.messages import HumanMessage, SystemMessage

from application.memory import MemoryBundle, MemoryOrchestrator, MemoryUpdateService
from application.story_memory import build_story_memory_payload
from config import settings
from models.story import (
    Message,
    RetrievedContext,
    StoryContext,
    StoryGenerationRequest,
    StoryGenerationResponse,
)
from models.story_runtime import (
    ScriptConsistencyCheckResult,
    ScriptRoundContract,
    ScriptRuntimeState,
)
from prompting import render_prompt
from services.conversation_history_manager import ConversationHistoryManager
from services.lorebook_manager import LorebookManager
from services.lorebook_compressor import LorebookCompressor
from services.summary_memory_manager import SummaryMemoryManager
from services.story_generation.context_helpers import (
    format_conversation_history,
    format_retrieved_contexts,
)
from services.story_generation.llm_factory import (
    detect_provider,
    estimate_tokens,
    get_env_api_key,
    normalize_usage,
)
from services.story_generation.prompt_builder import build_system_prompt

# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)


class StoryGenerator:
    """故事生成编排器。"""

    def __init__(
        self,
        lorebook_manager: LorebookManager,
        history_manager: Optional[ConversationHistoryManager] = None,
        llm_gateway: Optional[LLMGateway] = None,
        world_manager=None,
        roleplay_manager=None,
        script_design_app=None,
        summary_memory_manager: Optional[SummaryMemoryManager] = None,
        story_runtime_manager=None,
        entity_state_manager=None,
        entity_state_fallback_service=None,
        entity_patch_update_service=None,
        entity_state_event_replay_service=None,
    ):
        """初始化故事生成编排器。

        大部分依赖为可选注入，用于兼容不同部署阶段与测试场景。
        """
        self.lorebook_manager = lorebook_manager
        self.history_manager = history_manager
        self.llm_gateway = llm_gateway
        self.world_manager = world_manager
        self.roleplay_manager = roleplay_manager
        self.script_design_app = script_design_app
        self.summary_memory_manager = summary_memory_manager
        self.story_runtime_manager = story_runtime_manager
        self.entity_state_manager = entity_state_manager
        self.entity_state_fallback_service = entity_state_fallback_service
        self.entity_patch_update_service = entity_patch_update_service
        self.entity_state_event_replay_service = entity_state_event_replay_service
        self.lorebook_compressor = LorebookCompressor()
        self.recent_message_count = 5
        self.memory_orchestrator = MemoryOrchestrator(
            lorebook_manager=self.lorebook_manager,
            history_manager=self.history_manager,
            world_manager=self.world_manager,
            roleplay_manager=self.roleplay_manager,
            script_design_app=self.script_design_app,
            summary_memory_manager=self.summary_memory_manager,
            story_runtime_manager=self.story_runtime_manager,
            entity_state_event_replay_service=self.entity_state_event_replay_service,
            recent_message_count=self.recent_message_count,
        )
        self.memory_update_service = MemoryUpdateService(
            history_manager=self.history_manager,
            summary_memory_manager=self.summary_memory_manager,
            recent_message_count=self.recent_message_count,
        )

        # 流式生成后供 metadata 接口复用的缓存（同一次流式会话内有效）。
        self._last_retrieved_contexts: List[Dict[str, Any]] = []
        self._last_retrieved_history: List[Dict[str, Any]] = []
        self._last_activation_logs: List[Dict[str, Any]] = []

        logger.info("StoryGenerator initialized with hybrid memory mode")

    # ------------------------------------------------------------------
    # 输入质量增强
    # ------------------------------------------------------------------

    # P1-A: 基于叙事基调的 temperature 偏移量
    _TONE_TEMP_OFFSET: Dict[str, float] = {
        "dark": -0.15, "serious": -0.15, "tense": -0.15,
        "horror": -0.10, "mystery": -0.05,
        "romantic": 0.10, "epic": 0.05, "humorous": 0.10,
        "comedy": 0.10, "intimate": 0.05,
    }
    _ENHANCE_INPUT_MAX_CHARS: int = 40

    @staticmethod
    def _resolve_temperature(
        base_temp: Optional[float],
        world_config: Optional[Dict[str, Any]],
    ) -> float:
        """根据 narrative_tone 微调 temperature（±0.15），不改变用户显式设置的大方向。"""
        base = base_temp or settings.default_temperature
        tone = (world_config or {}).get("narrative_tone", "")
        offset = StoryGenerator._TONE_TEMP_OFFSET.get(str(tone).lower(), 0.0)
        resolved = max(0.3, min(1.5, base + offset))
        if offset != 0.0:
            logger.debug("🌡️ temperature 自适应: base=%.2f, tone=%s, offset=%+.2f → %.2f", base, tone, offset, resolved)
        return resolved

    @staticmethod
    def _detect_input_loop(user_input: str, recent_messages: List[Message]) -> bool:
        """检测用户输入是否与最近 3 条 user 消息高度重复（bigram Jaccard > 0.75）。"""
        def _bigrams(text: str) -> set:
            """将文本切分为 bigram 集合，用于近似重复度比较。"""
            chars = text.strip()
            if len(chars) < 2:
                return {chars}
            return {chars[i:i + 2] for i in range(len(chars) - 1)}

        current_bi = _bigrams(user_input)
        if not current_bi:
            return False

        user_msgs = [m.content for m in recent_messages if m.role == "user"][-3:]
        for prev in user_msgs:
            prev_bi = _bigrams(prev)
            if not prev_bi:
                continue
            intersection = current_bi & prev_bi
            union = current_bi | prev_bi
            if union and len(intersection) / len(union) > 0.75:
                logger.info("🔁 检测到重复输入: jaccard=%.2f", len(intersection) / len(union))
                return True
        return False

    @staticmethod
    def _should_enhance_input(user_input: str) -> bool:
        """仅对较短输入执行扩写，避免无意义二次改写。"""
        text = user_input.strip()
        return bool(text) and len(text) <= StoryGenerator._ENHANCE_INPUT_MAX_CHARS

    @staticmethod
    def _build_enhance_context_hint(
        context: StoryContext,
        retrieved_contexts: List[Dict[str, Any]],
    ) -> str:
        """构建输入扩写的轻量上下文提示。"""
        parts: List[str] = []
        if context.current_location:
            parts.append(f"地点: {context.current_location}")
        if context.active_characters:
            parts.append(f"人物: {', '.join(context.active_characters[:4])}")
        if context.messages:
            recent_assistant = [m.content for m in context.messages if m.role == "assistant"][-1:]
            if recent_assistant:
                parts.append(f"上一段情节: {recent_assistant[0][:120]}")
        if retrieved_contexts:
            names = [str(item.get("name", "")).strip() for item in retrieved_contexts[:3] if item.get("name")]
            if names:
                parts.append(f"相关设定: {', '.join(names)}")
        return "；".join(parts)

    async def _enhance_user_input(
        self,
        user_input: str,
        context_hint: str,
        llm: Any,
    ) -> str:
        """异步扩写输入。失败时回退原始输入。"""
        text = (user_input or "").strip()
        if not self._should_enhance_input(text):
            return text

        prompt = render_prompt(
            "story.input_enhancement",
            context_hint=context_hint or "无",
            user_input=text,
        )
        try:
            response = await llm.ainvoke(prompt)
            enhanced = str(getattr(response, "content", "") or "").strip()
            if not enhanced:
                return text
            return enhanced.replace("\n", " ")[:120]
        except Exception as exc:
            logger.warning("输入扩写失败，回退原文: %s", exc)
            return text

    def _enhance_user_input_sync(
        self,
        user_input: str,
        context_hint: str,
        llm: Any,
    ) -> str:
        """同步扩写输入。失败时回退原始输入。"""
        text = (user_input or "").strip()
        if not self._should_enhance_input(text):
            return text

        prompt = render_prompt(
            "story.input_enhancement",
            context_hint=context_hint or "无",
            user_input=text,
        )
        try:
            response = llm.invoke(prompt)
            enhanced = str(getattr(response, "content", "") or "").strip()
            if not enhanced:
                return text
            return enhanced.replace("\n", " ")[:120]
        except Exception as exc:
            logger.warning("输入扩写失败，回退原文(sync): %s", exc)
            return text

    # ------------------------------------------------------------------
    # 兼容保留：原私有方法名不变，内部委托给拆分模块
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_provider(model: str) -> str:
        """兼容保留：委托给 `llm_factory.detect_provider`。"""
        return detect_provider(model)

    @staticmethod
    def _get_env_api_key(provider: str) -> Optional[str]:
        """兼容保留：按 provider 读取环境变量 API Key。"""
        return get_env_api_key(provider)

    @staticmethod
    def _normalize_usage(usage_obj: Any) -> Optional[Dict[str, int]]:
        """兼容保留：归一化 provider 返回的 token 用量结构。"""
        return normalize_usage(usage_obj)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """兼容保留：估算文本 token 数，用于流式回退统计。"""
        return estimate_tokens(text)

    def _get_llm(
        self,
        model: Optional[str] = None,
        temperature: float = 0.95,
        max_tokens: Optional[int] = None,
        user_id: Optional[str] = None,
        for_streaming: bool = False,
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """统一创建 LLM 客户端。

        支持用户级配置覆盖、provider/base_url 显式指定以及流式/非流式模式。
        """
        if self.llm_gateway is None:
            raise RuntimeError("LLM gateway is not configured for StoryGenerator")
        return self.llm_gateway.create_client(
            model=model,
            provider=provider,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            user_id=user_id,
            for_streaming=for_streaming,
        )

    def _build_system_prompt(
        self,
        retrieved_contexts: Optional[List[Dict[str, Any]]] = None,
        retrieved_history: List[Dict[str, Any]] = None,
        style: str = "narrative",
        language: str = "zh-CN",
        world_config: Optional[Dict[str, Any]] = None,
        roleplay_profile: Optional[Dict[str, Any]] = None,
        summary_memory: Optional[Dict[str, Any]] = None,
        authors_note: Optional[str] = None,
        mode: Optional[str] = None,
        instruction: Optional[str] = None,
        focus_instruction: Optional[str] = None,
        focus_label: Optional[str] = None,
        script_design_context: Optional[Dict[str, Any]] = None,
        bundle: Optional[MemoryBundle] = None,
    ) -> str:
        """构建系统提示词，内部委托提示词构建器模块。"""
        return build_system_prompt(
            retrieved_contexts=retrieved_contexts,
            retrieved_history=retrieved_history,
            style=style,
            language=language,
            world_config=world_config,
            roleplay_profile=roleplay_profile,
            summary_memory=summary_memory,
            authors_note=authors_note,
            mode=mode,
            instruction=instruction,
            focus_instruction=focus_instruction,
            focus_label=focus_label,
            script_design_context=script_design_context,
            bundle=bundle,
        )

    def _build_memory_bundle(
        self,
        *,
        request: StoryGenerationRequest,
        context: StoryContext,
        owner_user_id: Optional[str] = None,
        history_k: int,
        history_score_threshold: Optional[float] = None,
        assistant_weight: Optional[float] = None,
        log_prefix: str = "",
    ) -> Dict[str, Any]:
        """构建分层记忆包并抽取主流程常用字段。

        返回值是对 MemoryOrchestrator 结果的轻量适配，方便主流程直接消费。
        """
        result = self.memory_orchestrator.build_bundle(
            request=request,
            context=context,
            owner_user_id=owner_user_id,
            history_k=history_k,
            history_score_threshold=history_score_threshold,
            assistant_weight=assistant_weight,
            log_prefix=log_prefix,
        )
        bundle = result["bundle"]
        return {
            "bundle": bundle,
            "world_id": result["world_id"],
            "activation_logs": result["activation_logs"],
            "retrieved_contexts": list((bundle.get("world") or {}).get("retrieved_lore") or []),
            "retrieved_history": list((bundle.get("episodic") or {}).get("recalled_episodes") or []),
            "world_config": dict((bundle.get("world") or {}).get("world_config") or {}),
        }

    @staticmethod
    def _sync_bundle_retrieved_contexts(
        bundle: MemoryBundle,
        retrieved_contexts: List[Dict[str, Any]],
    ) -> None:
        """将压缩/筛选后的检索上下文回写到 bundle 的 world 层。"""
        world_layer = dict(bundle.get("world") or {})
        world_layer["retrieved_lore"] = list(retrieved_contexts or [])
        bundle["world"] = world_layer

    def _build_prompt_history(self, bundle: Optional[MemoryBundle]) -> List[Any]:
        """从 episodic 层提取可注入提示词的历史消息。"""
        episodic = bundle.get("episodic") or {} if bundle else {}
        recent_messages = [
            Message(
                role=str(item.get("role") or ""),
                content=str(item.get("content") or ""),
            )
            for item in list(episodic.get("recent_messages") or [])
            if item.get("role") in {"user", "assistant"} and item.get("content")
        ]
        return self._format_conversation_history(
            recent_messages,
            max_history=len(recent_messages),
        )

    def _format_conversation_history(
        self,
        messages: List[Message],
        max_history: int = 10,
    ) -> List[Any]:
        """格式化对话历史为模型可消费消息序列。"""
        return format_conversation_history(messages, max_history=max_history)

    def _format_retrieved_contexts(
        self,
        retrieved_contexts: List[Dict[str, Any]],
        retrieved_history: List[Dict[str, Any]],
        history_name_template: str = "Turn {turn} - {role}",
    ) -> List[RetrievedContext]:
        """将检索上下文与历史命中统一映射为接口输出模型。"""
        return format_retrieved_contexts(
            retrieved_contexts,
            retrieved_history,
            history_name_template=history_name_template,
        )

    def _resolve_story_id(self, request: StoryGenerationRequest) -> Optional[str]:
        """优先读取请求中的 story_id，缺失时由 session_id 推导。"""
        story_id = getattr(request, "story_id", None)
        if story_id:
            return str(story_id)
        if not self.story_runtime_manager:
            return None
        return self.story_runtime_manager.derive_story_id(request.session_id)

    def _prepare_scripted_request(
        self,
        request: StoryGenerationRequest,
        activation_logs: List[Dict[str, Any]],
        *,
        owner_user_id: Optional[str] = None,
    ) -> tuple[
        StoryGenerationRequest,
        Optional[ScriptRuntimeState],
        Optional[ScriptRoundContract],
        Optional[Any],
    ]:
        """在严格剧本模式下预处理请求。

        包括：运行时状态确保、回合合同构建、RAG 范围约束注入、以及
        失败时自动回退到即兴模式（并记录 activation_logs）。
        """
        if request.creation_mode != "scripted" or not self.story_runtime_manager or not self.script_design_app:
            return request, None, None, None

        story_id = self._resolve_story_id(request)
        # 缺 story_id 无法定位 runtime，直接回退即兴模式。
        if not story_id:
            activation_logs.append(
                {
                    "source": "script_runtime",
                    "event": "fallback_improv",
                    "reason": "missing_story_id",
                }
            )
            request.creation_mode = "improv"
            return request, None, None, None

        script_design_id = getattr(request, "script_design_id", None)
        # 缺 script_design_id 无法构建 round contract，直接回退。
        if not script_design_id:
            activation_logs.append(
                {
                    "source": "script_runtime",
                    "event": "fallback_improv",
                    "reason": "missing_script_design_id",
                }
            )
            request.creation_mode = "improv"
            return request, None, None, None

        script_design = self.script_design_app.get_script_design(
            script_design_id,
            owner_user_id=owner_user_id,
        )
        # 请求给出的剧本不存在时回退，避免硬失败中断生成。
        if script_design is None:
            activation_logs.append(
                {
                    "source": "script_runtime",
                    "event": "fallback_improv",
                    "reason": "script_design_not_found",
                    "script_design_id": script_design_id,
                }
            )
            request.creation_mode = "improv"
            return request, None, None, None

        runtime_state = self.story_runtime_manager.ensure_runtime_state(
            story_id=story_id,
            session_id=request.session_id,
            world_id=request.world_id,
            script_design_id=script_design_id,
            creation_mode=request.creation_mode,
            owner_user_id=owner_user_id,
            preferred_stage_id=getattr(request, "active_stage_id", None),
            preferred_event_id=getattr(request, "active_event_id", None),
        )
        contract = self.story_runtime_manager.build_round_contract(
            script_design=script_design,
            runtime_state=runtime_state,
            progress_intent=getattr(request, "progress_intent", "hold"),
        )

        request.follow_script_design = True
        request.active_stage_id = contract.stage_id
        request.active_event_id = contract.event_id
        request.runtime_state_id = runtime_state.id
        request.story_id = story_id
        request.rag_scope_entry_ids = list(contract.rag_scope_entry_ids or [])

        if contract.progress_intent == "hold":
            intent_note = "本轮仅描写当前阶段与事件，不要自动完成主线节点。"
        elif contract.progress_intent == "advance":
            intent_note = "本轮应明确推进当前事件，但不要跳过结构化过程。"
        else:
            intent_note = "本轮可以尝试完成当前事件，但必须满足事件目标与预期结果。"

        strict_instruction_lines = [
            "【严格剧本模式】",
            "- 本轮必须以结构化剧本状态为主，不得由即兴灵感改写主线。",
            f"- 当前阶段: {contract.stage_title or '未指定'}",
            f"- 当前事件: {contract.event_title or '未指定'}",
            f"- 推进意图: {contract.progress_intent}",
            f"- 约束说明: {intent_note}",
        ]
        if contract.stage_goal:
            strict_instruction_lines.append(f"- 阶段目标: {contract.stage_goal}")
        if contract.event_objective:
            strict_instruction_lines.append(f"- 事件目标: {contract.event_objective}")
        if contract.event_obstacle:
            strict_instruction_lines.append(f"- 当前阻碍: {contract.event_obstacle}")
        if contract.completion_guard:
            strict_instruction_lines.append(f"- 完成条件: {contract.completion_guard}")

        strict_note = "\n".join(strict_instruction_lines)
        if request.focus_instruction:
            request.focus_instruction = f"{request.focus_instruction}\n{strict_note}"
        else:
            request.focus_instruction = strict_note
            if not request.focus_label:
                request.focus_label = "严格剧本推进"

        activation_logs.append(
            {
                "source": "script_runtime",
                "event": "prepared",
                "story_id": story_id,
                "runtime_state_id": runtime_state.id,
                "stage_id": contract.stage_id,
                "event_id": contract.event_id,
                "progress_intent": contract.progress_intent,
            }
        )
        return request, runtime_state, contract, script_design

    def _fallback_entity_state_after_generation(
        self,
        *,
        request: StoryGenerationRequest,
        world_id: Optional[str],
        context: StoryContext,
        memory_update_count: int,
        source: str,
        activation_logs: List[Dict[str, Any]],
    ) -> tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """在 patch 路径不可用时，通过 fallback 服务重建实体状态。"""
        if self.entity_state_fallback_service is None:
            return None, []

        story_id = self._resolve_story_id(request)
        if not story_id:
            return None, []

        entity_rebuild = self.entity_state_fallback_service.rebuild_session_state(
            session_id=request.session_id,
            story_id=story_id,
            world_id=world_id,
            messages=context.messages,
            source=source,
            operation_id=getattr(request, "memory_operation_id", None),
            sequence_start=int(getattr(request, "memory_operation_sequence_start", 1) or 1)
            + memory_update_count,
            activation_logs=activation_logs,
        )
        if not entity_rebuild.rebuilt:
            return None, []
        return self.entity_state_fallback_service.to_snapshot_payload(entity_rebuild), entity_rebuild.memory_updates

    @staticmethod
    def _normalize_entity_update_result(result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """标准化实体更新结果结构，保证下游字段稳定。"""
        payload = dict(result or {})
        return {
            "entity_state_snapshot": payload.get("entity_state_snapshot"),
            "entity_state_updates": list(payload.get("entity_state_updates") or []),
            "world_update": payload.get("world_update"),
            "memory_updates": list(payload.get("memory_updates") or []),
            "warnings": list(payload.get("warnings") or []),
            "used_fallback_rebuild": bool(payload.get("used_fallback_rebuild", False)),
        }

    async def _update_entity_state_after_generation_async(
        self,
        *,
        request: StoryGenerationRequest,
        world_id: Optional[str],
        context: StoryContext,
        generated_text: str,
        llm: Any,
        patch_llm: Any | None = None,
        memory_update_count: int,
        source: str,
        activation_logs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """异步更新实体状态。

        优先走 patch 流程；patch 失败时回退 fallback 全量重建。
        """
        operation_id = getattr(request, "memory_operation_id", None)
        sequence_start = int(getattr(request, "memory_operation_sequence_start", 1) or 1) + memory_update_count

        if self.entity_patch_update_service is not None:
            try:
                return self._normalize_entity_update_result(
                    await self.entity_patch_update_service.process_async(
                        request=request,
                        world_id=world_id,
                        generated_text=generated_text,
                        llm=patch_llm or llm,
                        source=source,
                        operation_id=operation_id,
                        sequence_start=sequence_start,
                        activation_logs=activation_logs,
                    )
                )
            except Exception as exc:
                logger.warning("Entity patch async orchestration failed, fallback to rebuild: %s", exc)
                activation_logs.append(
                    {
                        "source": "entity_patch",
                        "event": "orchestration_failed",
                        "reason": str(exc),
                    }
                )

        entity_state_snapshot, entity_state_updates = self._fallback_entity_state_after_generation(
            request=request,
            world_id=world_id,
            context=context,
            memory_update_count=memory_update_count,
            source=source,
            activation_logs=activation_logs,
        )
        return self._normalize_entity_update_result(
            {
                "entity_state_snapshot": entity_state_snapshot,
                "entity_state_updates": [],
                "world_update": None,
                "memory_updates": entity_state_updates,
            }
        )

    def _update_entity_state_after_generation_sync(
        self,
        *,
        request: StoryGenerationRequest,
        world_id: Optional[str],
        context: StoryContext,
        generated_text: str,
        llm: Any,
        patch_llm: Any | None = None,
        memory_update_count: int,
        source: str,
        activation_logs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """同步更新实体状态。

        优先走 patch 流程；patch 失败时回退 fallback 全量重建。
        """
        operation_id = getattr(request, "memory_operation_id", None)
        sequence_start = int(getattr(request, "memory_operation_sequence_start", 1) or 1) + memory_update_count

        if self.entity_patch_update_service is not None:
            try:
                return self._normalize_entity_update_result(
                    self.entity_patch_update_service.process_sync(
                        request=request,
                        world_id=world_id,
                        generated_text=generated_text,
                        llm=patch_llm or llm,
                        source=source,
                        operation_id=operation_id,
                        sequence_start=sequence_start,
                        activation_logs=activation_logs,
                    )
                )
            except Exception as exc:
                logger.warning("Entity patch sync orchestration failed, fallback to rebuild: %s", exc)
                activation_logs.append(
                    {
                        "source": "entity_patch",
                        "event": "orchestration_failed",
                        "reason": str(exc),
                    }
                )

        entity_state_snapshot, entity_state_updates = self._fallback_entity_state_after_generation(
            request=request,
            world_id=world_id,
            context=context,
            memory_update_count=memory_update_count,
            source=source,
            activation_logs=activation_logs,
        )
        return self._normalize_entity_update_result(
            {
                "entity_state_snapshot": entity_state_snapshot,
                "entity_state_updates": [],
                "world_update": None,
                "memory_updates": entity_state_updates,
            }
        )

    def _apply_scripted_post_generation(
        self,
        *,
        request: StoryGenerationRequest,
        generated_text: str,
        activation_logs: List[Dict[str, Any]],
        runtime_state: Optional[ScriptRuntimeState],
        contract: Optional[ScriptRoundContract],
        script_design: Optional[Any],
    ) -> tuple[Optional[ScriptRuntimeState], Optional[ScriptConsistencyCheckResult]]:
        """应用严格剧本后处理。

        顺序：一致性检查 -> runtime 状态推进 -> story 元数据同步。
        """
        if (
            request.creation_mode != "scripted"
            or not self.story_runtime_manager
            or runtime_state is None
            or contract is None
            or script_design is None
        ):
            return None, None

        check_result = self.story_runtime_manager.run_consistency_check(
            generated_text=generated_text,
            contract=contract,
        )
        updated_runtime = self.story_runtime_manager.apply_generation_result(
            runtime_state=runtime_state,
            script_design=script_design,
            contract=contract,
            check_result=check_result,
            allow_state_transition=bool(getattr(request, "allow_state_transition", True)),
        )
        self.story_runtime_manager.sync_story_metadata(updated_runtime)
        activation_logs.append(
            {
                "source": "script_runtime",
                "event": "checked",
                "passed": check_result.passed,
                "runtime_state_id": updated_runtime.id,
                "next_stage_id": updated_runtime.current_stage_id,
                "next_event_id": updated_runtime.current_event_id,
            }
        )
        return updated_runtime, check_result

    # ------------------------------------------------------------------
    # 生成主流程
    # ------------------------------------------------------------------

    async def generate_story(
        self,
        request: StoryGenerationRequest,
        user_id: Optional[str] = None,
    ) -> StoryGenerationResponse:
        """异步故事生成（非流式）。

        主流程：
        1) 预处理请求（必要时进入 strict scripted 约束）；
        2) 构建 memory bundle 与 system prompt；
        3) 调用 LLM 生成正文；
        4) 生成后更新（消息/摘要/实体）并返回完整响应。
        """
        start_time = time.time()

        context = request.context or StoryContext(session_id=request.session_id, messages=[])
        activation_logs: List[Dict[str, Any]] = []
        request, runtime_state, round_contract, script_design = self._prepare_scripted_request(
            request,
            activation_logs,
            owner_user_id=user_id,
        )

        # 组装分层记忆并展开主流程常用字段。
        memory_state = self._build_memory_bundle(
            request=request,
            context=context,
            owner_user_id=user_id,
            history_k=5,
        )
        bundle = memory_state["bundle"]
        retrieved_contexts = memory_state["retrieved_contexts"]
        retrieved_history = memory_state["retrieved_history"]
        world_id = memory_state["world_id"]
        activation_logs.extend(memory_state["activation_logs"])
        world_config = memory_state["world_config"]

        # P1-A: 自适应 temperature（提前创建 LLM 供压缩与输入扩写复用）
        llm = self._get_llm(
            model=request.model,
            temperature=self._resolve_temperature(request.temperature, world_config),
            user_id=user_id,
            provider=getattr(request, "provider", None),
            base_url=getattr(request, "base_url", None),
        )

        # P3-B: 可选输入扩写（仅短输入）
        effective_user_input = request.user_input
        if getattr(request, "enhance_input", False):
            hint = self._build_enhance_context_hint(context, retrieved_contexts)
            enhanced = await self._enhance_user_input(request.user_input, hint, llm)
            if enhanced and enhanced != request.user_input:
                effective_user_input = enhanced
                activation_logs.append(
                    {
                        "source": "input_enhancer",
                        "event": "applied",
                        "original_len": len(request.user_input),
                        "enhanced_len": len(enhanced),
                    }
                )

        # P0-B: 反循环检测
        if self._detect_input_loop(request.user_input, context.messages):
            effective_user_input += "\n[叙事提示：请推进新的情节，不要重复已发生的动作或场景]"

        # 由 prompt_builder 统一拼装系统提示词（含预算裁剪）。
        system_prompt = self._build_system_prompt(
            style=request.style or "narrative",
            language=request.language,
            bundle=bundle,
        )

        context.messages.append(Message(role="user", content=request.user_input))

        history = self._build_prompt_history(bundle)

        messages = [
            SystemMessage(content=system_prompt),
            *history,
            HumanMessage(content=effective_user_input),
        ]

        response = await llm.ainvoke(messages)
        generated_text = response.content
        tokens_used = self._normalize_usage(getattr(response, "usage_metadata", None))

        context.messages.append(Message(role="assistant", content=generated_text))
        updated_runtime_state, consistency_check = self._apply_scripted_post_generation(
            request=request,
            generated_text=generated_text,
            activation_logs=activation_logs,
            runtime_state=runtime_state,
            contract=round_contract,
            script_design=script_design,
        )

        # 先写 episodic/semantic，再基于生成结果更新 entity 层。
        update_result = self.memory_update_service.run_post_generation_updates(
            session_id=request.session_id,
            world_id=world_id,
            owner_user_id=user_id,
            context=context,
            user_input=request.user_input,
            assistant_output=generated_text,
            activation_logs=activation_logs,
            summary_update_mode="sync",
            llm=llm,
            source="generate",
            operation_id=getattr(request, "memory_operation_id", None),
            sequence_start=int(getattr(request, "memory_operation_sequence_start", 1) or 1),
        )
        updated_summary = update_result["summary_snapshot"]
        memory_updates = update_result["memory_updates"]
        entity_update_result = await self._update_entity_state_after_generation_async(
            request=request,
            world_id=world_id,
            context=context,
            generated_text=generated_text,
            llm=llm,
            memory_update_count=len(memory_updates),
            source="generate",
            activation_logs=activation_logs,
        )
        memory_updates = list(memory_updates) + list(entity_update_result["memory_updates"])

        generation_time = time.time() - start_time
        formatted_contexts = self._format_retrieved_contexts(retrieved_contexts, retrieved_history)

        runtime_snapshot = updated_runtime_state.model_dump(mode="json") if updated_runtime_state else None
        return StoryGenerationResponse(
            session_id=request.session_id,
            user_input=request.user_input,
            generated_text=generated_text,
            retrieved_contexts=formatted_contexts,
            updated_context=context,
            activation_logs=activation_logs,
            memory_updates=memory_updates,
            story_memory=build_story_memory_payload(
                session_id=request.session_id,
                story_id=request.story_id,
                world_id=world_id,
                summary_memory_snapshot=updated_summary,
                runtime_state_snapshot=runtime_snapshot,
                entity_state_snapshot=entity_update_result["entity_state_snapshot"],
                entity_state_updates=entity_update_result["entity_state_updates"],
                world_update=entity_update_result["world_update"],
                memory_updates=memory_updates,
            ),
            summary_memory_snapshot=updated_summary,
            runtime_state_snapshot=runtime_snapshot,
            entity_state_snapshot=entity_update_result["entity_state_snapshot"],
            entity_state_updates=entity_update_result["entity_state_updates"],
            world_update=entity_update_result["world_update"],
            creation_mode=request.creation_mode,
            consistency_check=(
                consistency_check.model_dump(mode="json") if consistency_check else None
            ),
            model_used=request.model or settings.default_model,
            tokens_used=tokens_used,
            token_source="provider_usage" if tokens_used else None,
            generation_time=generation_time,
        )

    async def preview_enhanced_input(
        self,
        request: StoryGenerationRequest,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """预览短输入增强结果，不执行正式故事生成。"""
        text = (request.user_input or "").strip()
        if not text:
            return {
                "original_text": "",
                "enhanced_text": "",
                "applied": False,
                "reason": "empty_input",
            }

        if not self._should_enhance_input(text):
            return {
                "original_text": text,
                "enhanced_text": text,
                "applied": False,
                "reason": "input_too_long",
            }

        context = request.context or StoryContext(session_id=request.session_id, messages=[])
        preview_logs: List[Dict[str, Any]] = []
        request, _, _, _ = self._prepare_scripted_request(
            request,
            preview_logs,
            owner_user_id=user_id,
        )
        memory_state = self._build_memory_bundle(
            request=request,
            context=context,
            owner_user_id=user_id,
            history_k=5,
        )
        retrieved_contexts = memory_state["retrieved_contexts"]
        world_config = memory_state["world_config"]
        llm = self._get_llm(
            model=request.model,
            temperature=self._resolve_temperature(request.temperature, world_config),
            user_id=user_id,
            provider=getattr(request, "provider", None),
            base_url=getattr(request, "base_url", None),
        )
        hint = self._build_enhance_context_hint(context, retrieved_contexts)
        enhanced = await self._enhance_user_input(text, hint, llm)
        return {
            "original_text": text,
            "enhanced_text": enhanced,
            "applied": enhanced != text,
            "reason": "enhanced" if enhanced != text else "unchanged",
        }

    def generate_story_sync(
        self,
        request: StoryGenerationRequest,
        user_id: Optional[str] = None,
    ) -> StoryGenerationResponse:
        """同步故事生成。

        与 `generate_story` 流程等价，差异在于 LLM/压缩/实体更新路径均为同步调用。
        """
        start_time = time.time()

        context = request.context or StoryContext(session_id=request.session_id, messages=[])
        activation_logs: List[Dict[str, Any]] = []
        request, runtime_state, round_contract, script_design = self._prepare_scripted_request(
            request,
            activation_logs,
            owner_user_id=user_id,
        )

        memory_state = self._build_memory_bundle(
            request=request,
            context=context,
            owner_user_id=user_id,
            history_k=3,
        )
        bundle = memory_state["bundle"]
        retrieved_contexts = memory_state["retrieved_contexts"]
        retrieved_history = memory_state["retrieved_history"]
        world_id = memory_state["world_id"]
        activation_logs.extend(memory_state["activation_logs"])
        world_config = memory_state["world_config"]

        # P1-A: 自适应 temperature（提前创建 LLM 供压缩与输入扩写复用）
        llm = self._get_llm(
            model=request.model,
            temperature=self._resolve_temperature(request.temperature, world_config),
            user_id=user_id,
            provider=getattr(request, "provider", None),
            base_url=getattr(request, "base_url", None),
        )

        # P3-B: 可选输入扩写（仅短输入）
        effective_user_input = request.user_input
        if getattr(request, "enhance_input", False):
            hint = self._build_enhance_context_hint(context, retrieved_contexts)
            enhanced = self._enhance_user_input_sync(request.user_input, hint, llm)
            if enhanced and enhanced != request.user_input:
                effective_user_input = enhanced
                activation_logs.append(
                    {
                        "source": "input_enhancer",
                        "event": "applied",
                        "original_len": len(request.user_input),
                        "enhanced_len": len(enhanced),
                    }
                )

        # P0-B: 反循环检测
        if self._detect_input_loop(request.user_input, context.messages):
            effective_user_input += "\n[叙事提示：请推进新的情节，不要重复已发生的动作或场景]"

        # P2-C: 长条目压缩（同步）
        retrieved_contexts = self.lorebook_compressor.compress_contexts_sync(retrieved_contexts, llm)
        self._sync_bundle_retrieved_contexts(bundle, retrieved_contexts)

        system_prompt = self._build_system_prompt(
            style=request.style or "narrative",
            language=request.language,
            bundle=bundle,
        )

        context.messages.append(Message(role="user", content=request.user_input))

        history = self._build_prompt_history(bundle)

        messages = [
            SystemMessage(content=system_prompt),
            *history,
            HumanMessage(content=effective_user_input),
        ]

        response = llm.invoke(messages)
        generated_text = response.content
        tokens_used_sync = self._normalize_usage(getattr(response, "usage_metadata", None))

        context.messages.append(Message(role="assistant", content=generated_text))
        updated_runtime_state, consistency_check = self._apply_scripted_post_generation(
            request=request,
            generated_text=generated_text,
            activation_logs=activation_logs,
            runtime_state=runtime_state,
            contract=round_contract,
            script_design=script_design,
        )

        update_result = self.memory_update_service.run_post_generation_updates(
            session_id=request.session_id,
            world_id=world_id,
            owner_user_id=user_id,
            context=context,
            user_input=request.user_input,
            assistant_output=generated_text,
            activation_logs=activation_logs,
            summary_update_mode="sync",
            log_prefix="(sync) ",
            source="generate",
            operation_id=getattr(request, "memory_operation_id", None),
            sequence_start=int(getattr(request, "memory_operation_sequence_start", 1) or 1),
        )
        updated_summary = update_result["summary_snapshot"]
        memory_updates = update_result["memory_updates"]
        entity_update_result = self._update_entity_state_after_generation_sync(
            request=request,
            world_id=world_id,
            context=context,
            generated_text=generated_text,
            llm=llm,
            memory_update_count=len(memory_updates),
            source="generate",
            activation_logs=activation_logs,
        )
        memory_updates = list(memory_updates) + list(entity_update_result["memory_updates"])

        generation_time = time.time() - start_time
        formatted_contexts = self._format_retrieved_contexts(retrieved_contexts, retrieved_history)

        runtime_snapshot = updated_runtime_state.model_dump(mode="json") if updated_runtime_state else None
        return StoryGenerationResponse(
            session_id=request.session_id,
            user_input=request.user_input,
            generated_text=generated_text,
            retrieved_contexts=formatted_contexts,
            updated_context=context,
            activation_logs=activation_logs,
            memory_updates=memory_updates,
            story_memory=build_story_memory_payload(
                session_id=request.session_id,
                story_id=request.story_id,
                world_id=world_id,
                summary_memory_snapshot=updated_summary,
                runtime_state_snapshot=runtime_snapshot,
                entity_state_snapshot=entity_update_result["entity_state_snapshot"],
                entity_state_updates=entity_update_result["entity_state_updates"],
                world_update=entity_update_result["world_update"],
                memory_updates=memory_updates,
            ),
            summary_memory_snapshot=updated_summary,
            runtime_state_snapshot=runtime_snapshot,
            entity_state_snapshot=entity_update_result["entity_state_snapshot"],
            entity_state_updates=entity_update_result["entity_state_updates"],
            world_update=entity_update_result["world_update"],
            creation_mode=request.creation_mode,
            consistency_check=(
                consistency_check.model_dump(mode="json") if consistency_check else None
            ),
            model_used=request.model or settings.default_model,
            tokens_used=tokens_used_sync,
            token_source="provider_usage" if tokens_used_sync else None,
            generation_time=generation_time,
        )

    async def generate_story_stream(
        self,
        request: StoryGenerationRequest,
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """异步流式故事生成。

        SSE 协议：先连续输出 chunk 事件，最后输出一条 done 事件携带完整元数据。
        """
        context = request.context or StoryContext(session_id=request.session_id, messages=[])
        activation_logs: List[Dict[str, Any]] = []
        request, runtime_state, round_contract, script_design = self._prepare_scripted_request(
            request,
            activation_logs,
            owner_user_id=user_id,
        )

        memory_state = self._build_memory_bundle(
            request=request,
            context=context,
            owner_user_id=user_id,
            history_k=5,
            history_score_threshold=0.35,
            assistant_weight=1.3,
            log_prefix="🔍 ",
        )
        bundle = memory_state["bundle"]
        retrieved_contexts = memory_state["retrieved_contexts"]
        retrieved_history = memory_state["retrieved_history"]
        world_id = memory_state["world_id"]
        activation_logs.extend(memory_state["activation_logs"])
        world_config = memory_state["world_config"]

        logger.info("🌍 世界设定检索结果: %s 条", len(retrieved_contexts))
        for context_item in retrieved_contexts:
            logger.info("  📍 [%s] %s", context_item.get("type", "unknown"), context_item.get("name", "unnamed"))

        if retrieved_history:
            logger.info("✅ 检索到 %s 条相关历史对话", len(retrieved_history))
            for history_item in retrieved_history:
                role_label = "玩家动作" if history_item["role"] == "user" else "故事情节"
                logger.info(
                    "  📖 [%s] Turn#%s: %s...",
                    role_label,
                    history_item["turn_number"],
                    history_item["content"][:80],
                )
        else:
            logger.info("⏭️ 跳过历史检索或无命中: messages=%s", len(context.messages))

        self._last_retrieved_contexts = retrieved_contexts
        self._last_retrieved_history = retrieved_history
        self._last_activation_logs = activation_logs
        logger.info(
            "💾 缓存检索结果: contexts=%s, history=%s",
            len(self._last_retrieved_contexts),
            len(self._last_retrieved_history),
        )

        # 前处理专用 LLM：输入增强 / lorebook 压缩 / patch 抽取。
        preprocess_llm = self._get_llm(
            model=request.model,
            temperature=self._resolve_temperature(request.temperature, world_config),
            max_tokens=request.max_tokens,
            user_id=user_id,
            for_streaming=False,
            provider=getattr(request, "provider", None),
            base_url=getattr(request, "base_url", None),
        )

        # 正文流式输出专用 LLM：仅用于 astream。
        llm = self._get_llm(
            model=request.model,
            temperature=self._resolve_temperature(request.temperature, world_config),
            max_tokens=request.max_tokens,
            user_id=user_id,
            for_streaming=True,
            provider=getattr(request, "provider", None),
            base_url=getattr(request, "base_url", None),
        )

        # P3-B: 可选输入扩写（仅短输入）
        effective_user_input = request.user_input
        if getattr(request, "enhance_input", False):
            hint = self._build_enhance_context_hint(context, retrieved_contexts)
            enhanced = await self._enhance_user_input(request.user_input, hint, preprocess_llm)
            if enhanced and enhanced != request.user_input:
                effective_user_input = enhanced
                self._last_activation_logs.append(
                    {
                        "source": "input_enhancer",
                        "event": "applied",
                        "original_len": len(request.user_input),
                        "enhanced_len": len(enhanced),
                    }
                )

        # P0-B: 反循环检测
        if self._detect_input_loop(request.user_input, context.messages):
            effective_user_input += "\n[叙事提示：请推进新的情节，不要重复已发生的动作或场景]"

        # P2-C: 长条目压缩
        retrieved_contexts = await self.lorebook_compressor.compress_contexts(
            retrieved_contexts,
            preprocess_llm,
        )
        self._last_retrieved_contexts = retrieved_contexts
        self._sync_bundle_retrieved_contexts(bundle, retrieved_contexts)

        system_prompt = self._build_system_prompt(
            style=request.style or "narrative",
            language=request.language,
            bundle=bundle,
        )

        context.messages.append(Message(role="user", content=request.user_input))

        history = self._build_prompt_history(bundle)

        messages = [
            SystemMessage(content=system_prompt),
            *history,
            HumanMessage(content=effective_user_input),
        ]

        full_text = ""
        accumulated_chunk = None
        stream_start = time.time()

        async for chunk in llm.astream(messages):
            if hasattr(chunk, "content") and chunk.content:
                full_text += chunk.content
                yield f"data: {json.dumps({'chunk': chunk.content, 'done': False}, ensure_ascii=False)}\n\n"
            try:
                accumulated_chunk = chunk if accumulated_chunk is None else accumulated_chunk + chunk
            except Exception:
                pass

        context.messages.append(Message(role="assistant", content=full_text))
        updated_runtime_state, consistency_check = self._apply_scripted_post_generation(
            request=request,
            generated_text=full_text,
            activation_logs=self._last_activation_logs,
            runtime_state=runtime_state,
            contract=round_contract,
            script_design=script_design,
        )

        update_result = self.memory_update_service.run_post_generation_updates(
            session_id=request.session_id,
            world_id=world_id,
            owner_user_id=user_id,
            context=context,
            user_input=request.user_input,
            assistant_output=full_text,
            activation_logs=self._last_activation_logs,
            summary_update_mode="sync",
            llm=preprocess_llm,
            log_prefix="(stream) ",
            source="generate",
            operation_id=getattr(request, "memory_operation_id", None),
            sequence_start=int(getattr(request, "memory_operation_sequence_start", 1) or 1),
        )
        updated_summary = update_result["summary_snapshot"]
        memory_updates = update_result["memory_updates"]
        entity_update_result = await self._update_entity_state_after_generation_async(
            request=request,
            world_id=world_id,
            context=context,
            generated_text=full_text,
            llm=llm,
            patch_llm=preprocess_llm,
            memory_update_count=len(memory_updates),
            source="generate",
            activation_logs=self._last_activation_logs,
        )
        memory_updates = list(memory_updates) + list(entity_update_result["memory_updates"])

        generation_time = time.time() - stream_start
        formatted_contexts = self._format_retrieved_contexts(
            self._last_retrieved_contexts,
            self._last_retrieved_history,
        )

        normalized_usage: Optional[Dict[str, int]] = None
        prompt_tok = 0
        compl_tok = 0
        total_tok = 0
        token_source = "estimated"

        try:
            from services import analytics_service as _analytics

            stream_usage = getattr(accumulated_chunk, "usage_metadata", None) if accumulated_chunk else None
            normalized_usage = self._normalize_usage(stream_usage)
            if normalized_usage:
                prompt_tok = normalized_usage["input_tokens"]
                compl_tok = normalized_usage["output_tokens"]
                total_tok = normalized_usage["total_tokens"]
                token_source = "provider_usage"
            else:
                prompt_tok = self._estimate_tokens(system_prompt)
                prompt_tok += sum(self._estimate_tokens(str(msg.content)) for msg in history)
                prompt_tok += self._estimate_tokens(request.user_input)
                compl_tok = self._estimate_tokens(full_text)
                total_tok = prompt_tok + compl_tok

            _analytics.record_event(
                event_type="story_generate",
                session_id=request.session_id,
                world_id=world_id,
                model=request.model or settings.default_model,
                success=True,
                generation_time=generation_time,
                prompt_tokens=prompt_tok,
                completion_tokens=compl_tok,
                total_tokens=total_tok,
                token_source=token_source,
                retrieved_context_count=len(formatted_contexts),
            )
        except Exception:
            pass

        final_tokens = normalized_usage or {
            "input_tokens": prompt_tok,
            "output_tokens": compl_tok,
            "total_tokens": total_tok,
        }

        runtime_snapshot = updated_runtime_state.model_dump(mode="json") if updated_runtime_state else None
        # done 事件返回最终文本、记忆更新与统计信息，供前端一次性落库。
        done_payload = {
            "done": True,
            "session_id": request.session_id,
            "model": request.model or settings.default_model,
            "generation_time": generation_time,
            "generated_text": full_text,
            "output_text": full_text,
            "contexts": [
                {"name": item.entry_name, "type": item.entry_type, "score": item.relevance_score}
                for item in formatted_contexts
            ],
            "activation_logs": self._last_activation_logs,
            "memory_updates": memory_updates,
            "story_memory": build_story_memory_payload(
                session_id=request.session_id,
                story_id=request.story_id,
                world_id=world_id,
                summary_memory_snapshot=updated_summary,
                runtime_state_snapshot=runtime_snapshot,
                entity_state_snapshot=entity_update_result["entity_state_snapshot"],
                entity_state_updates=entity_update_result["entity_state_updates"],
                world_update=entity_update_result["world_update"],
                memory_updates=memory_updates,
            ),
            "summary_memory_snapshot": updated_summary,
            "runtime_state_snapshot": runtime_snapshot,
            "entity_state_snapshot": entity_update_result["entity_state_snapshot"],
            "entity_state_updates": entity_update_result["entity_state_updates"],
            "world_update": entity_update_result["world_update"],
            "creation_mode": request.creation_mode,
            "consistency_check": (
                consistency_check.model_dump(mode="json") if consistency_check else None
            ),
            "tokens_used": final_tokens,
            "token_source": token_source,
        }
        yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

    async def get_generation_metadata(
        self,
        request: StoryGenerationRequest,
        generated_text: str,
    ) -> StoryGenerationResponse:
        """流式生成结束后返回结构化元数据。

        该接口复用流式阶段缓存的检索结果，避免重复触发 RAG 查询。
        """
        context = request.context or StoryContext(session_id=request.session_id, messages=[])

        logger.info(
            "📤 get_generation_metadata: cached_contexts=%s, cached_history=%s",
            len(self._last_retrieved_contexts),
            len(self._last_retrieved_history),
        )

        formatted_contexts = [
            RetrievedContext(
                entry_name=ctx["name"],
                entry_type=ctx["type"],
                content=ctx["content"],
                relevance_score=ctx["relevance_score"],
            )
            for ctx in self._last_retrieved_contexts
        ]

        for hist in self._last_retrieved_history:
            formatted_contexts.append(
                RetrievedContext(
                    entry_name=f"历史对话 Turn#{hist['turn_number']} ({hist['role']})",
                    entry_type="conversation_history",
                    content=hist["content"][:200] + "..." if len(hist["content"]) > 200 else hist["content"],
                    relevance_score=hist["relevance_score"],
                )
            )

        if self._last_retrieved_history:
            logger.info("📚 返回 %s 条历史引用到前端", len(self._last_retrieved_history))

        return StoryGenerationResponse(
            session_id=request.session_id,
            user_input=request.user_input,
            generated_text=generated_text,
            retrieved_contexts=formatted_contexts,
            updated_context=context,
            activation_logs=self._last_activation_logs,
            memory_updates=[],
            model_used=request.model or settings.default_model,
            tokens_used=None,
            token_source=None,
            generation_time=0.0,
        )
