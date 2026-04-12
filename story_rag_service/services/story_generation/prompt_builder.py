"""
系统提示词构建逻辑（PromptComponent 架构）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from application.memory import MemoryBundle
from prompting import render_prompt

# 变量作用：模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)

# 为 recent history / user input 预留空间，控制 system prompt 上限
SYSTEM_PROMPT_TOKEN_BUDGET = 3200


def _estimate_tokens_fast(text: str) -> int:
    """轻量 token 估算（避免循环导入 llm_factory）。"""
    if not text:
        return 0
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff" or "\u3000" <= ch <= "\u30ff")
    return max(1, int(cjk * 1.7 + (len(text) - cjk) * 0.25))


class PromptComponent:
    """提示词组件基类。"""

    name: str = "base"
    priority: int = 100
    required: bool = False
    enabled: bool = True

    def render(self, **context: Any) -> str:
        """功能：处理 render。"""
        raise NotImplementedError

    def estimate_tokens(self, text: str) -> int:
        """功能：处理 estimate Token。"""
        return _estimate_tokens_fast(text)


@dataclass
class RenderedComponent:
    """作用：定义 RenderedComponent 类型，承载本模块核心状态与行为。"""
    component: PromptComponent
    text: str
    tokens: int


class WorldContextComponent(PromptComponent):
    """作用：定义 WorldContextComponent 类型，承载本模块核心状态与行为。"""
    name = "WorldContextComponent"
    priority = 50

    def render(self, **context: Any) -> str:
        """功能：处理 render。"""
        return render_prompt(
            "story.world_context",
            retrieved_contexts=list(context.get("retrieved_contexts") or []),
        )


class HistoryContextComponent(PromptComponent):
    """作用：定义 HistoryContextComponent 类型，承载本模块核心状态与行为。"""
    name = "HistoryContextComponent"
    priority = 10

    def render(self, **context: Any) -> str:
        """功能：处理 render。"""
        return render_prompt(
            "story.history_context",
            retrieved_history=list(context.get("retrieved_history") or []),
        )


class SummaryMemoryComponent(PromptComponent):
    """作用：定义 SummaryMemoryComponent 类型，承载本模块核心状态与行为。"""
    name = "SummaryMemoryComponent"
    priority = 40

    def render(self, **context: Any) -> str:
        """功能：处理 render。"""
        return render_prompt(
            "story.summary_memory",
            summary_memory=context.get("summary_memory") or {},
        )


class StyleComponent(PromptComponent):
    """作用：定义 StyleComponent 类型，承载本模块核心状态与行为。"""
    name = "StyleComponent"
    priority = 30

    def render(self, **context: Any) -> str:
        """功能：处理 render。"""
        return render_prompt("story.style", world_config=context.get("world_config") or {})


class AtmosphereComponent(PromptComponent):
    """作用：定义 AtmosphereComponent 类型，承载本模块核心状态与行为。"""
    name = "AtmosphereComponent"
    priority = 20

    def render(self, **context: Any) -> str:
        """功能：处理 render。"""
        return render_prompt("story.atmosphere", world_config=context.get("world_config") or {})


class RoleplayComponent(PromptComponent):
    """作用：定义 RoleplayComponent 类型，承载本模块核心状态与行为。"""
    name = "RoleplayComponent"
    priority = 80
    required = True

    def render(self, **context: Any) -> str:
        """功能：处理 render。"""
        return render_prompt(
            "story.roleplay",
            roleplay_profile=context.get("roleplay_profile") or {},
        )


class DialogueControlComponent(PromptComponent):
    """作用：定义 DialogueControlComponent 类型，承载本模块核心状态与行为。"""
    name = "DialogueControlComponent"
    priority = 82

    def render(self, **context: Any) -> str:
        """功能：处理 render。"""
        controls = context.get("dialogue_controls") or {}
        principal_character_id = controls.get("principal_character_id")
        dialogue_target = controls.get("dialogue_target")
        dialogue_intent = controls.get("dialogue_intent")
        dialogue_style_hint = controls.get("dialogue_style_hint")
        dialogue_mode = controls.get("dialogue_mode") or "auto"
        force_dialogue_round = bool(controls.get("force_dialogue_round", False))

        if not any([
            principal_character_id,
            dialogue_target,
            dialogue_intent,
            dialogue_style_hint,
            force_dialogue_round,
        ]):
            return ""

        lines = ["【关键角色交流控制】"]
        if principal_character_id:
            lines.append(f"- 本轮关键角色条目ID: {principal_character_id}")
            lines.append("- 若上下文中存在该角色，请优先让其参与当前段落的互动或对白。")
        lines.append(f"- 对白模式: {dialogue_mode}")
        if dialogue_target:
            lines.append(f"- 对话目标: {dialogue_target}")
        if dialogue_intent:
            lines.append(f"- 对话意图: {dialogue_intent}")
        if dialogue_style_hint:
            lines.append(f"- 对白风格提示: {dialogue_style_hint}")
        if force_dialogue_round:
            lines.append("- 本轮必须出现能体现角色身份的明确对白，而不是只做背景描写。")
        elif dialogue_mode == "focused":
            lines.append("- 优先安排关键角色在本轮中发声，但仍可保留必要叙事。")
        return "\n".join(lines)


class ScriptDesignComponent(PromptComponent):
    """作用：定义 ScriptDesignComponent 类型，承载本模块核心状态与行为。"""
    name = "ScriptDesignComponent"
    priority = 84

    def render(self, **context: Any) -> str:
        """功能：处理 render。"""
        script_guidance = context.get("script_guidance") or {}
        if not script_guidance or not script_guidance.get("follow_script_design"):
            return ""

        active_stage = script_guidance.get("active_stage") or {}
        active_event = script_guidance.get("active_event") or {}
        foreshadows = script_guidance.get("highlighted_foreshadows") or []

        lines = ["【剧本设计约束】"]
        if script_guidance.get("title"):
            lines.append(f"- 当前剧本: {script_guidance['title']}")
        if script_guidance.get("logline"):
            lines.append(f"- 主线概括: {script_guidance['logline']}")
        if script_guidance.get("summary"):
            lines.append(f"- 剧本摘要: {script_guidance['summary']}")
        if script_guidance.get("theme"):
            lines.append(f"- 主题: {script_guidance['theme']}")
        if script_guidance.get("core_conflict"):
            lines.append(f"- 核心冲突: {script_guidance['core_conflict']}")
        if active_stage:
            lines.append(f"- 当前阶段: {active_stage.get('title')}")
            if active_stage.get("goal"):
                lines.append(f"- 阶段目标: {active_stage['goal']}")
            if active_stage.get("tension"):
                lines.append(f"- 阶段张力: {active_stage['tension']}")
        if active_event:
            lines.append(f"- 当前事件: {active_event.get('title')}")
            if active_event.get("objective"):
                lines.append(f"- 事件目标: {active_event['objective']}")
            if active_event.get("obstacle"):
                lines.append(f"- 主要阻碍: {active_event['obstacle']}")
            if active_event.get("expected_outcome"):
                lines.append(f"- 理想结果: {active_event['expected_outcome']}")
        if foreshadows:
            lines.append("- 本轮需留意的未回收伏笔:")
            for item in foreshadows:
                title = item.get("title") or "未命名伏笔"
                content = item.get("content") or ""
                lines.append(f"  * {title}: {content}")
        lines.append("- 输出不得明显偏离当前阶段和事件目标，除非用户明确要求跳出主线。")
        return "\n".join(lines)


class CoreInstructionComponent(PromptComponent):
    """作用：定义 CoreInstructionComponent 类型，承载本模块核心状态与行为。"""
    name = "CoreInstructionComponent"
    priority = 90
    required = True

    def render(self, **context: Any) -> str:
        """功能：处理 render。"""
        return render_prompt(
            "story.core_instruction",
            style=str(context.get("style") or "narrative"),
            language=str(context.get("language") or "zh-CN"),
            authors_note=context.get("authors_note"),
            mode=str(context.get("mode") or "narrative"),
            instruction=context.get("instruction"),
            focus_instruction=context.get("focus_instruction"),
            focus_label=context.get("focus_label"),
        )


def _trim_to_budget(rendered: List[RenderedComponent], budget: int) -> List[RenderedComponent]:
    """按组件优先级裁剪可选组件，直到满足预算。"""
    if not rendered:
        return []

    total = sum(item.tokens for item in rendered)
    if total <= budget:
        return rendered

    keep = list(rendered)
    candidates = sorted(
        [item for item in keep if not item.component.required],
        key=lambda item: item.component.priority,
    )

    for item in candidates:
        if total <= budget:
            break
        try:
            keep.remove(item)
            total -= item.tokens
            logger.info(
                "🔪 Prompt budget trim: component=%s priority=%d tokens=%d total=%d/%d",
                item.component.name,
                item.component.priority,
                item.tokens,
                total,
                budget,
            )
        except ValueError:
            continue

    return keep


def _build_components() -> List[PromptComponent]:
    """功能：构建 components。"""
    return [
        HistoryContextComponent(),
        AtmosphereComponent(),
        StyleComponent(),
        SummaryMemoryComponent(),
        WorldContextComponent(),
        RoleplayComponent(),
        DialogueControlComponent(),
        ScriptDesignComponent(),
        CoreInstructionComponent(),
    ]


def _normalize_prompt_context(
    *,
    bundle: Optional[MemoryBundle],
    retrieved_contexts: Optional[List[Dict[str, Any]]],
    retrieved_history: Optional[List[Dict[str, Any]]],
    style: str,
    language: str,
    world_config: Optional[Dict[str, Any]],
    roleplay_profile: Optional[Dict[str, Any]],
    summary_memory: Optional[Dict[str, Any]],
    authors_note: Optional[str],
    mode: Optional[str],
    instruction: Optional[str],
    focus_instruction: Optional[str],
    focus_label: Optional[str],
    dialogue_controls: Optional[Dict[str, Any]],
    script_guidance: Optional[Dict[str, Any]],
    script_design_context: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """功能：标准化 prompt 上下文。"""
    if not bundle:
        normalized_dialogue_controls = dialogue_controls
        if normalized_dialogue_controls is None:
            normalized_dialogue_controls = dict((roleplay_profile or {}).get("dialogue_controls") or {})

        return {
            "retrieved_contexts": list(retrieved_contexts or []),
            "retrieved_history": retrieved_history,
            "style": style,
            "language": language,
            "world_config": world_config,
            "roleplay_profile": roleplay_profile,
            "summary_memory": summary_memory,
            "authors_note": authors_note,
            "mode": mode or "narrative",
            "instruction": instruction,
            "focus_instruction": focus_instruction,
            "focus_label": focus_label,
            "dialogue_controls": normalized_dialogue_controls,
            "script_guidance": script_guidance or script_design_context or {},
            "script_design_context": script_design_context,
        }

    episodic = bundle.get("episodic") or {}
    semantic = bundle.get("semantic") or {}
    profile = bundle.get("profile") or {}
    procedural = bundle.get("procedural") or {}
    world = bundle.get("world") or {}

    normalized_summary = summary_memory or semantic.get("raw_record") or {
        "summary_text": semantic.get("summary_text", ""),
        "key_facts": list(semantic.get("key_facts") or []),
        "entities": dict(semantic.get("entities") or {}),
    }

    normalized_roleplay_profile = roleplay_profile or profile.get("raw_profile") or {
        "persona": profile.get("persona"),
        "character_card": profile.get("character_card"),
        "story_state": profile.get("story_state"),
    }

    return {
        "retrieved_contexts": list(retrieved_contexts or world.get("retrieved_lore") or []),
        "retrieved_history": retrieved_history if retrieved_history is not None else list(episodic.get("recalled_episodes") or []),
        "style": style,
        "language": language,
        "world_config": world_config or world.get("world_config") or {},
        "roleplay_profile": normalized_roleplay_profile,
        "summary_memory": normalized_summary,
        "authors_note": authors_note if authors_note is not None else procedural.get("authors_note"),
        "mode": mode or procedural.get("mode") or "narrative",
        "instruction": instruction if instruction is not None else procedural.get("instruction"),
        "focus_instruction": focus_instruction if focus_instruction is not None else procedural.get("focus_instruction"),
        "focus_label": focus_label if focus_label is not None else procedural.get("focus_label"),
        "dialogue_controls": dialogue_controls if dialogue_controls is not None else dict(procedural.get("dialogue_controls") or {}),
        "script_guidance": script_guidance or procedural.get("script_guidance") or procedural.get("script_design_context") or {},
        "script_design_context": script_design_context or procedural.get("script_design_context") or {},
    }


def build_system_prompt(
    *,
    retrieved_contexts: Optional[List[Dict[str, Any]]] = None,
    retrieved_history: Optional[List[Dict[str, Any]]] = None,
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
    dialogue_controls: Optional[Dict[str, Any]] = None,
    script_guidance: Optional[Dict[str, Any]] = None,
    script_design_context: Optional[Dict[str, Any]] = None,
    bundle: Optional[MemoryBundle] = None,
) -> str:
    """构建故事生成系统提示词（对外签名保持兼容）。"""
    context = _normalize_prompt_context(
        bundle=bundle,
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
        dialogue_controls=dialogue_controls,
        script_guidance=script_guidance,
        script_design_context=script_design_context,
    )

    rendered: List[RenderedComponent] = []
    for component in sorted(_build_components(), key=lambda comp: comp.priority):
        if not component.enabled:
            continue
        text = component.render(**context).strip()
        if not text:
            continue
        rendered.append(
            RenderedComponent(
                component=component,
                text=text,
                tokens=component.estimate_tokens(text),
            )
        )

    trimmed = _trim_to_budget(rendered, SYSTEM_PROMPT_TOKEN_BUDGET)
    prompt = "\n\n".join(item.text for item in trimmed).strip()
    return prompt
