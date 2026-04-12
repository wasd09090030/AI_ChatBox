"""Central prompt registry and renderers for backend prompt templates."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from models.story_style import PRESET_STYLE_TEMPLATES, get_style_prompt_segment

# 变量作用：变量 PromptRenderer，用于保存 promptrenderer 相关模块级状态。
PromptRenderer = Callable[..., str]


def _render_world_context(*, retrieved_contexts: List[Dict[str, Any]] | None = None, **_: Any) -> str:
    """功能：处理 render 世界观上下文。"""
    context_list = list(retrieved_contexts or [])
    if not context_list:
        return ""

    type_map = {
        "world_setting": "世界观",
        "character": "角色",
        "location": "地点",
        "event": "事件",
    }

    def format_contexts(items: List[Dict[str, Any]]) -> str:
        """功能：格式化 contexts。"""
        if not items:
            return ""
        lines = ["【相关世界设定】"]
        for ctx in items:
            entry_type = str(ctx.get("type", "unknown"))
            type_label = type_map.get(entry_type, entry_type)
            name = str(ctx.get("name", "Unknown"))
            content = str(ctx.get("content", ""))
            lines.append(f"## {name} ({type_label})")
            lines.append(content)
        return "\n".join(lines).strip()

    before_char = [item for item in context_list if item.get("insertion_position") == "before_char"]
    after_char = [item for item in context_list if item.get("insertion_position") != "before_char"]
    return "\n\n".join(part for part in (format_contexts(before_char), format_contexts(after_char)) if part).strip()


def _render_history_context(*, retrieved_history: List[Dict[str, Any]] | None = None, **_: Any) -> str:
    """功能：处理 render 历史上下文。"""
    history_list = list(retrieved_history or [])
    if not history_list:
        return ""

    lines = [
        "【相关历史情节】",
        "以下是更早之前的故事片段，可作为背景参考：",
    ]
    for hist in history_list:
        role_label = "玩家行动" if hist.get("role") == "user" else "故事情节"
        content = str(hist.get("content", ""))
        lines.append(f"- [{role_label}] {content[:150]}...")
    return "\n".join(lines).strip()


def _render_summary_memory(*, summary_memory: Dict[str, Any] | None = None, **_: Any) -> str:
    """功能：处理 render 摘要记忆。"""
    summary = summary_memory or {}
    summary_text = str(summary.get("summary_text", "")).strip()
    if not summary_text:
        return ""

    lines = ["【摘要记忆】", summary_text]

    facts = summary.get("key_facts") or []
    if facts:
        lines.append("关键事实: " + "；".join(str(item) for item in facts[:8]))

    entities = summary.get("entities") or {}
    entity_parts: List[str] = []
    for label, key in (("人物", "characters"), ("地点", "locations"), ("物品", "items")):
        items = entities.get(key) or []
        if items:
            entity_parts.append(f"{label}[{'、'.join(str(item) for item in items[:6])}]")
    if entity_parts:
        lines.append("已知实体: " + " | ".join(entity_parts))

    return "\n".join(lines).strip()


def _render_style(*, world_config: Dict[str, Any] | None = None, **_: Any) -> str:
    """功能：处理 render style。"""
    config = world_config or {}
    if not config:
        return ""

    style_preset = config.get("style_preset")
    if style_preset and style_preset in PRESET_STYLE_TEMPLATES:
        style_template = PRESET_STYLE_TEMPLATES[style_preset]
        return f"【风格模板 - {style_preset}】\n{get_style_prompt_segment(style_template)}"

    tone_names = {
        "light": "轻松明快",
        "dark": "阴郁黑暗",
        "serious": "严肃正经",
        "humorous": "幽默诙谐",
        "mysterious": "神秘莫测",
        "romantic": "浪漫唯美",
        "epic": "史诗宏大",
        "intimate": "细腻私密",
        "tense": "紧张刺激",
    }
    pacing_names = {
        "fast": "快节奏",
        "moderate": "中等节奏",
        "slow": "慢节奏",
        "variable": "随情节变化",
    }

    parts: List[str] = []
    if config.get("narrative_tone"):
        tone = str(config["narrative_tone"])
        parts.append(f"- 叙事基调: {tone_names.get(tone, tone)}")
    if config.get("pacing_style"):
        pacing = str(config["pacing_style"])
        parts.append(f"- 叙事节奏: {pacing_names.get(pacing, pacing)}")
    if config.get("vocabulary_style"):
        parts.append(f"- 语言风格: {config['vocabulary_style']}")
    if config.get("style_tags"):
        parts.append(f"- 风格要素: {', '.join(config['style_tags'])}")

    if not parts:
        return ""
    return "【写作风格配置】\n" + "\n".join(parts)


def _render_atmosphere(*, world_config: Dict[str, Any] | None = None, **_: Any) -> str:
    """功能：处理 render atmosphere。"""
    config = world_config or {}
    if not config:
        return ""

    time_names = {
        "dawn": "黎明时分",
        "morning": "清晨",
        "noon": "正午时分",
        "afternoon": "下午",
        "dusk": "黄昏",
        "evening": "傍晚",
        "night": "夜晚",
        "midnight": "深夜",
    }
    weather_names = {
        "clear": "晴朗",
        "cloudy": "多云",
        "overcast": "阴天",
        "rain": "雨天",
        "heavy_rain": "暴雨",
        "snow": "雪天",
        "fog": "雾气弥漫",
        "storm": "风暴",
    }

    parts: List[str] = []
    if config.get("default_time_of_day"):
        key = str(config["default_time_of_day"])
        parts.append(f"默认时间: {time_names.get(key, key)}")
    if config.get("default_weather"):
        key = str(config["default_weather"])
        parts.append(f"默认天气: {weather_names.get(key, key)}")
    if config.get("default_mood"):
        parts.append(f"默认氛围: {config['default_mood']}")

    if not parts:
        return ""
    return "【默认场景氛围】\n" + "\n".join(parts) + "\n（请在描写中自然融入这些氛围元素，使用五感细节增强沉浸感）"


def _render_roleplay(*, roleplay_profile: Dict[str, Any] | None = None, **_: Any) -> str:
    """功能：处理 render roleplay。"""
    profile = roleplay_profile or {}
    if not profile:
        return ""

    roleplay_parts: List[str] = []
    character_card = profile.get("character_card")
    if character_card:
        lines = [f"角色名: {character_card.get('name', '未命名角色')}"]
        if character_card.get("description"):
            lines.append(f"角色描述: {character_card['description']}")
        if character_card.get("system_prompt"):
            lines.append(f"角色规则: {character_card['system_prompt']}")
        if character_card.get("first_message"):
            lines.append(f"开场示例: {character_card['first_message']}")
        examples = character_card.get("example_messages") or []
        if examples:
            lines.append(f"语气示例: {' | '.join(examples[:2])}")
        roleplay_parts.append("【角色卡】\n" + "\n".join(lines))

    persona = profile.get("persona")
    if persona:
        lines = [f"主角名: {persona.get('name', '未命名主角')}"]
        if persona.get("title"):
            lines.append(f"主角头衔: {persona['title']}")
        if persona.get("description"):
            lines.append(f"主角设定: {persona['description']}")
        traits = persona.get("traits") or []
        if traits:
            lines.append(f"主角特征: {', '.join(traits[:6])}")
        roleplay_parts.append("【主角人设】\n" + "\n".join(lines))

    story_state_mode = profile.get("story_state_mode", "off")
    story_state = profile.get("story_state")
    if story_state_mode != "off" and story_state:
        state_lines: List[str] = []
        if story_state.get("chapter"):
            state_lines.append(f"当前章节: {story_state['chapter']}")
        if story_state.get("objective"):
            state_lines.append(f"当前目标: {story_state['objective']}")
        if story_state.get("conflict"):
            state_lines.append(f"主要冲突: {story_state['conflict']}")
        clues = story_state.get("clues") or []
        if clues and story_state_mode == "strict":
            state_lines.append(f"已知线索: {', '.join(clues[:6])}")
        if state_lines:
            mode_desc = "严格跟随" if story_state_mode == "strict" else "柔性参考"
            roleplay_parts.append("【剧情状态】\n" + "\n".join(state_lines) + f"\n状态模式: {mode_desc}")

    return "\n\n".join(roleplay_parts).strip()


def _render_story_core_instruction(
    *,
    style: str = "narrative",
    language: str = "zh-CN",
    authors_note: str | None = None,
    mode: str = "narrative",
    instruction: str | None = None,
    focus_instruction: str | None = None,
    focus_label: str | None = None,
    **_: Any,
) -> str:
    """功能：处理 render 故事 core instruction。"""
    dialogue_text = """【对话增强要求】
- 每个角色说话时需体现其独特语音特征（如已设定口头禅、说话风格、口音等）
- 对话中适当加入潜台词，让角色言外之意丰富
- 穿插肢体语言和微表情描写
- 适时展现角色内心独白
- 对话节奏张弛有度"""

    mode_text = ""
    if mode == "choices":
        mode_text = """【选项生成要求（强制执行）】
请在故事正文结束后另起一行，用以下格式输出三个玩家可选择的行动选项（不要在正文内容中嵌入这些标记）：
[A] 第一个选项描述
[B] 第二个选项描述
[C] 第三个选项描述
选项应该简洁（20字以内）、互相有所区别，并且都符合当前情节。"""
    elif mode == "instruction" and instruction:
        mode_text = f"【剧情强制指令】\n请确保本次回复中：{instruction}"

    authors_note_text = f"【作者旁白】\n{authors_note}" if authors_note else ""
    focus_title = str(focus_label or "本轮故事重点").strip()
    focus_text = f"【{focus_title}】\n{focus_instruction}" if focus_instruction else ""

    return f"""你是一位富有创造力的故事大师，擅长编写引人入胜的互动式故事。

【核心任务】
根据用户的最新输入，从上一次输出的末尾无缝衔接，继续推进故事。不要中断、重启场景或复述已经发生的动作。

【连贯性要求 - 最高优先级】
1. 时间连续：从上一段结束时刻继续，不跳跃、不倒退
2. 场景连续：保持角色所处地点和状态，除非用户明确改变
3. 情节承接：从上一句动作/对白继续推进，不要重新开场
4. 状态记忆：保持物件、角色在场、环境状态的一致性
5. 避免重复：不要重复刚刚发生的情节

【处理用户输入】
- 如果用户输入与当前状态冲突（如门已开却要求开门），请自然化解并推进剧情
- 如果输入模糊，基于当前上下文做最合理解释
- 可改变方向，但应平滑过渡，不要突兀跳转

【叙事技巧】
- 展示而非叙述：通过动作、对话、感官细节呈现情节
- 控制节奏：单次输出不要推进过多主线，保留互动空间
- 适度留白：在关键节点留下下一步选择空间
- 细节一致：保持前文信息一致性（地点、物件、人物状态）

【写作风格】
- 风格: {style}
- 语言: {language}
- 输出长度: 每次输出 200-500 个中文字符，保持细节和氛围
- 使用视觉、听觉、触觉、嗅觉等感官描写增强沉浸感

{dialogue_text}

【世界观一致性】
- 严格遵循既有世界设定、角色性格、规则约束
- 新引入元素需与世界观兼容
- 角色言行必须符合既有设定

【给予玩家主动权】
- 不要替玩家角色做关键决策
- 允许用户随时改变方向与策略
- NPC 可自主行动，但主角决策权始终归玩家

{authors_note_text}
{focus_text}
{mode_text}""".strip()


def _render_input_enhancement(*, context_hint: str, user_input: str, **_: Any) -> str:
    """功能：处理 render 输入增强。"""
    return (
        "你是互动小说输入优化器。请将用户的简短动作扩写为 1 句可执行行动描述，"
        "保留用户意图，不新增与意图冲突的信息，不超过 60 个中文字符。"
        "只输出扩写结果，不要解释。\n\n"
        f"上下文提示：{context_hint or '无'}\n"
        f"用户输入：{user_input}"
    )


def _render_summary_system(**_: Any) -> str:
    """功能：处理 render 摘要 system。"""
    return "你是一名专业的故事编辑，擅长简洁归纳情节。请严格输出JSON。"


def _render_summary_user(*, conversation_text: str, **_: Any) -> str:
    """功能：处理 render 摘要用户。"""
    return (
        "请将以下对话摘要为**200字以内**的叙事摘要，重点保留：\n"
        "- 人物关系变化\n- 重要决策及其后果\n- 当前目标/冲突\n- 已发现的关键线索\n\n"
        f"对话记录：\n{conversation_text}\n\n"
        "请严格按照以下JSON格式输出（不要加任何前缀或包裹markdown代码块）：\n"
        '{"summary": "摘要文本", "entities": {"characters": ["角色名"], "locations": ["地点名"], "items": ["物品名"]}}\n'
        "entities 中每个类别最多6个，没有的留空数组。"
    )


def _render_lorebook_compress(*, target: int, content: str, **_: Any) -> str:
    """功能：处理 render 知识库 compress。"""
    return (
        f"你是一个信息压缩工具。将以下文本精炼为不超过{target}字的摘要，保留关键信息（人名、地名、规则、数值）。"
        "只输出摘要文本，不加多余解释。\n\n"
        f"原文：\n{content}"
    )


# 变量作用：变量 PROMPT_RENDERERS，用于保存 prompt renderers 相关模块级状态。
PROMPT_RENDERERS: Dict[str, PromptRenderer] = {
    "story.world_context": _render_world_context,
    "story.history_context": _render_history_context,
    "story.summary_memory": _render_summary_memory,
    "story.style": _render_style,
    "story.atmosphere": _render_atmosphere,
    "story.roleplay": _render_roleplay,
    "story.core_instruction": _render_story_core_instruction,
    "story.input_enhancement": _render_input_enhancement,
    "summary.editor_system": _render_summary_system,
    "summary.user_memory_json": _render_summary_user,
    "lorebook.compress": _render_lorebook_compress,
}


def get_prompt_renderer(prompt_id: str) -> PromptRenderer:
    """功能：获取 prompt renderer。"""
    try:
        return PROMPT_RENDERERS[prompt_id]
    except KeyError as exc:
        raise KeyError(f"Unknown prompt template: {prompt_id}") from exc


def render_prompt(prompt_id: str, **context: Any) -> str:
    """功能：处理 render prompt。"""
    return get_prompt_renderer(prompt_id)(**context).strip()