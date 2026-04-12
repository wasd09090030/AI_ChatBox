"""
Story Style, Atmosphere, and Dialogue Enhancement Models
故事风格、场景氛围、对话增强模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


# ==================== 风格模板系统 ====================

class StyleGenre(str, Enum):
    """预设风格类型"""
    FANTASY = "fantasy"           # 奇幻
    WUXIA = "wuxia"              # 武侠
    XIANXIA = "xianxia"          # 仙侠
    NOIR = "noir"                # 黑色电影
    HORROR = "horror"            # 恐怖
    ROMANCE = "romance"          # 浪漫
    SCIFI = "scifi"              # 科幻
    MYSTERY = "mystery"          # 悬疑
    COMEDY = "comedy"            # 喜剧
    TRAGEDY = "tragedy"          # 悲剧
    ADVENTURE = "adventure"      # 冒险
    SLICE_OF_LIFE = "slice_of_life"  # 日常
    CUSTOM = "custom"            # 自定义


class NarrativeTone(str, Enum):
    """叙事基调"""
    LIGHT = "light"              # 轻松明快
    DARK = "dark"                # 阴郁黑暗
    SERIOUS = "serious"          # 严肃正经
    HUMOROUS = "humorous"        # 幽默诙谐
    MYSTERIOUS = "mysterious"    # 神秘莫测
    ROMANTIC = "romantic"        # 浪漫唯美
    EPIC = "epic"                # 史诗宏大
    INTIMATE = "intimate"        # 细腻私密
    TENSE = "tense"              # 紧张刺激


class PacingStyle(str, Enum):
    """叙事节奏"""
    FAST = "fast"                # 快节奏
    MODERATE = "moderate"        # 中等节奏
    SLOW = "slow"                # 慢节奏
    VARIABLE = "variable"        # 可变节奏


class StyleTemplate(BaseModel):
    """风格模板"""
    genre: StyleGenre = Field(default=StyleGenre.FANTASY, description="故事类型")
    tone: NarrativeTone = Field(default=NarrativeTone.LIGHT, description="叙事基调")
    pacing: PacingStyle = Field(default=PacingStyle.MODERATE, description="叙事节奏")
    
    # 词汇风格
    vocabulary_style: Optional[str] = Field(
        default=None,
        description="词汇风格描述，如'古风文言'、'现代口语'、'硬汉派简洁'等"
    )
    
    # 叙事视角
    narrative_perspective: str = Field(
        default="third_person_limited",
        description="叙事视角: first_person(第一人称), third_person_limited(第三人称有限), third_person_omniscient(第三人称全知)"
    )
    
    # 特殊风格标签
    style_tags: List[str] = Field(
        default_factory=list,
        description="风格标签，如['诗意', '血腥', '温馨', '哲学思辨']"
    )
    
    # 自定义风格描述
    custom_style_description: Optional[str] = Field(
        default=None,
        description="自定义风格的详细描述"
    )
    
    class Config:
        """Pydantic 配置：序列化时输出枚举值字符串。"""
        use_enum_values = True


# 预设风格模板
PRESET_STYLE_TEMPLATES: Dict[str, StyleTemplate] = {
    "fantasy": StyleTemplate(
        genre=StyleGenre.FANTASY,
        tone=NarrativeTone.EPIC,
        pacing=PacingStyle.MODERATE,
        vocabulary_style="奇幻史诗风格，富有想象力的描写",
        style_tags=["魔法", "冒险", "英雄之旅"]
    ),
    "wuxia": StyleTemplate(
        genre=StyleGenre.WUXIA,
        tone=NarrativeTone.SERIOUS,
        pacing=PacingStyle.VARIABLE,
        vocabulary_style="古风半文言，武侠小说风格",
        style_tags=["江湖", "侠义", "快意恩仇", "武功招式"]
    ),
    "xianxia": StyleTemplate(
        genre=StyleGenre.XIANXIA,
        tone=NarrativeTone.EPIC,
        pacing=PacingStyle.MODERATE,
        vocabulary_style="古风仙侠用语，境界修炼描写",
        style_tags=["修仙", "天道", "飞升", "法宝"]
    ),
    "noir": StyleTemplate(
        genre=StyleGenre.NOIR,
        tone=NarrativeTone.DARK,
        pacing=PacingStyle.SLOW,
        vocabulary_style="硬汉派简洁冷峻，内心独白丰富",
        style_tags=["黑暗", "犯罪", "道德灰色", "城市夜景"]
    ),
    "horror": StyleTemplate(
        genre=StyleGenre.HORROR,
        tone=NarrativeTone.TENSE,
        pacing=PacingStyle.VARIABLE,
        vocabulary_style="氛围渲染细腻，恐惧心理描写",
        style_tags=["恐怖", "悬疑", "心理压迫", "未知威胁"]
    ),
    "romance": StyleTemplate(
        genre=StyleGenre.ROMANCE,
        tone=NarrativeTone.ROMANTIC,
        pacing=PacingStyle.SLOW,
        vocabulary_style="细腻唯美，情感描写丰富",
        style_tags=["爱情", "心动", "浪漫", "情感纠葛"]
    ),
    "scifi": StyleTemplate(
        genre=StyleGenre.SCIFI,
        tone=NarrativeTone.SERIOUS,
        pacing=PacingStyle.MODERATE,
        vocabulary_style="科技感术语，逻辑严谨",
        style_tags=["科技", "未来", "太空", "人工智能"]
    ),
    "mystery": StyleTemplate(
        genre=StyleGenre.MYSTERY,
        tone=NarrativeTone.MYSTERIOUS,
        pacing=PacingStyle.SLOW,
        vocabulary_style="悬念铺设，细节暗示",
        style_tags=["推理", "线索", "真相", "反转"]
    ),
    "comedy": StyleTemplate(
        genre=StyleGenre.COMEDY,
        tone=NarrativeTone.HUMOROUS,
        pacing=PacingStyle.FAST,
        vocabulary_style="轻松幽默，对话机智",
        style_tags=["搞笑", "吐槽", "反差萌", "日常"]
    ),
    "slice_of_life": StyleTemplate(
        genre=StyleGenre.SLICE_OF_LIFE,
        tone=NarrativeTone.INTIMATE,
        pacing=PacingStyle.SLOW,
        vocabulary_style="生活化口语，温馨细腻",
        style_tags=["日常", "治愈", "温馨", "成长"]
    )
}


# ==================== 场景氛围增强 ====================

class TimeOfDay(str, Enum):
    """一天中的时间"""
    DAWN = "dawn"                # 黎明
    MORNING = "morning"          # 早晨
    NOON = "noon"                # 正午
    AFTERNOON = "afternoon"      # 下午
    DUSK = "dusk"                # 黄昏
    EVENING = "evening"          # 傍晚
    NIGHT = "night"              # 夜晚
    MIDNIGHT = "midnight"        # 深夜
    UNSPECIFIED = "unspecified"  # 未指定


class WeatherType(str, Enum):
    """天气类型"""
    CLEAR = "clear"              # 晴朗
    CLOUDY = "cloudy"            # 多云
    OVERCAST = "overcast"        # 阴天
    RAIN = "rain"                # 雨天
    HEAVY_RAIN = "heavy_rain"    # 暴雨
    SNOW = "snow"                # 雪天
    FOG = "fog"                  # 雾天
    STORM = "storm"              # 风暴
    WINDY = "windy"              # 大风
    HOT = "hot"                  # 炎热
    COLD = "cold"                # 寒冷
    UNSPECIFIED = "unspecified"  # 未指定


class SensoryDetails(BaseModel):
    """五感描写细节"""
    visual: List[str] = Field(
        default_factory=list,
        description="视觉描写元素，如['昏暗的烛光', '斑驳的墙壁', '飘落的雪花']"
    )
    auditory: List[str] = Field(
        default_factory=list,
        description="听觉描写元素，如['远处的钟声', '风声呼啸', '脚步声回响']"
    )
    olfactory: List[str] = Field(
        default_factory=list,
        description="嗅觉描写元素，如['潮湿的泥土味', '花香', '血腥味']"
    )
    tactile: List[str] = Field(
        default_factory=list,
        description="触觉描写元素，如['冰冷的石壁', '粗糙的树皮', '温暖的阳光']"
    )
    gustatory: List[str] = Field(
        default_factory=list,
        description="味觉描写元素，如['苦涩的药汤', '甘甜的泉水']"
    )


class SceneAtmosphere(BaseModel):
    """场景氛围设定"""
    time_of_day: TimeOfDay = Field(
        default=TimeOfDay.UNSPECIFIED,
        description="当前时间"
    )
    weather: WeatherType = Field(
        default=WeatherType.UNSPECIFIED,
        description="当前天气"
    )
    mood: Optional[str] = Field(
        default=None,
        description="场景情绪氛围，如'紧张'、'祥和'、'诡异'、'浪漫'"
    )
    lighting: Optional[str] = Field(
        default=None,
        description="光线描述，如'昏暗'、'明亮'、'烛光摇曳'"
    )
    sensory_details: SensoryDetails = Field(
        default_factory=SensoryDetails,
        description="五感描写细节"
    )
    ambient_sounds: List[str] = Field(
        default_factory=list,
        description="环境背景音，如['蝉鸣', '流水声', '远处的喧嚣']"
    )
    special_effects: List[str] = Field(
        default_factory=list,
        description="特殊效果，如['魔法光芒', '迷雾弥漫', '落叶纷飞']"
    )
    
    class Config:
        """Pydantic 配置：序列化时输出枚举值字符串。"""
        use_enum_values = True


# ==================== 对话增强系统 ====================

class SpeechPattern(BaseModel):
    """角色语音特征模式"""
    speaking_style: Optional[str] = Field(
        default=None,
        description="说话风格，如'文绉绉'、'粗犷豪放'、'温柔细语'、'冷淡简洁'"
    )
    accent: Optional[str] = Field(
        default=None,
        description="口音/方言，如'北方口音'、'江南软语'、'异域口音'"
    )
    verbal_tics: List[str] = Field(
        default_factory=list,
        description="口头禅/语癖，如['嗯...', '我说啊', '有意思']"
    )
    vocabulary_level: str = Field(
        default="normal",
        description="词汇水平: simple(简单), normal(普通), scholarly(文雅), archaic(古风)"
    )
    sentence_patterns: List[str] = Field(
        default_factory=list,
        description="常用句式模式，如['反问句多', '短句为主', '喜欢用比喻']"
    )
    emotional_expression: Optional[str] = Field(
        default=None,
        description="情感表达方式，如'内敛含蓄'、'热情奔放'、'面无表情'"
    )
    speech_examples: List[str] = Field(
        default_factory=list,
        description="台词示例，展示角色的说话方式"
    )


class DialogueEnhancement(BaseModel):
    """对话增强配置"""
    enable_subtext: bool = Field(
        default=True,
        description="是否启用潜台词暗示"
    )
    enable_body_language: bool = Field(
        default=True,
        description="是否启用肢体语言描写"
    )
    enable_internal_thoughts: bool = Field(
        default=True,
        description="是否启用内心独白"
    )
    dialogue_pacing: str = Field(
        default="balanced",
        description="对话节奏: rapid(快速交锋), balanced(平衡), deliberate(深思熟虑)"
    )
    tension_level: int = Field(
        default=5,
        ge=1,
        le=10,
        description="对话张力等级 1-10"
    )


# ==================== 综合增强配置 ====================

class StoryEnhancementConfig(BaseModel):
    """故事增强综合配置"""
    style_template: Optional[StyleTemplate] = Field(
        default=None,
        description="风格模板配置"
    )
    scene_atmosphere: Optional[SceneAtmosphere] = Field(
        default=None,
        description="场景氛围配置"
    )
    dialogue_enhancement: DialogueEnhancement = Field(
        default_factory=DialogueEnhancement,
        description="对话增强配置"
    )
    
    @classmethod
    def from_preset(cls, preset_name: str) -> "StoryEnhancementConfig":
        """从预设创建配置"""
        style = PRESET_STYLE_TEMPLATES.get(preset_name, PRESET_STYLE_TEMPLATES["fantasy"])
        return cls(style_template=style)


def get_style_prompt_segment(style: StyleTemplate) -> str:
    """
    根据风格模板生成 prompt 片段
    """
    segments = []
    
    # 类型和基调
    genre_names = {
        "fantasy": "奇幻", "wuxia": "武侠", "xianxia": "仙侠",
        "noir": "黑色电影", "horror": "恐怖", "romance": "浪漫",
        "scifi": "科幻", "mystery": "悬疑", "comedy": "喜剧",
        "tragedy": "悲剧", "adventure": "冒险", "slice_of_life": "日常"
    }
    tone_names = {
        "light": "轻松明快", "dark": "阴郁黑暗", "serious": "严肃正经",
        "humorous": "幽默诙谐", "mysterious": "神秘莫测", "romantic": "浪漫唯美",
        "epic": "史诗宏大", "intimate": "细腻私密", "tense": "紧张刺激"
    }
    pacing_names = {
        "fast": "快节奏推进", "moderate": "中等节奏", 
        "slow": "慢节奏细腻", "variable": "节奏随情节变化"
    }
    
    genre_name = genre_names.get(style.genre, style.genre)
    tone_name = tone_names.get(style.tone, style.tone)
    pacing_name = pacing_names.get(style.pacing, style.pacing)
    
    segments.append(f"- 故事类型: {genre_name}")
    segments.append(f"- 叙事基调: {tone_name}")
    segments.append(f"- 叙事节奏: {pacing_name}")
    
    if style.vocabulary_style:
        segments.append(f"- 语言风格: {style.vocabulary_style}")
    
    if style.style_tags:
        segments.append(f"- 风格要素: {', '.join(style.style_tags)}")
    
    if style.custom_style_description:
        segments.append(f"- 特殊要求: {style.custom_style_description}")
    
    return "\n".join(segments)


def get_atmosphere_prompt_segment(atmosphere: SceneAtmosphere) -> str:
    """
    根据场景氛围生成 prompt 片段
    """
    segments = []
    
    time_names = {
        "dawn": "黎明时分", "morning": "清晨", "noon": "正午时分",
        "afternoon": "下午", "dusk": "黄昏", "evening": "傍晚",
        "night": "夜晚", "midnight": "深夜"
    }
    weather_names = {
        "clear": "晴朗", "cloudy": "多云", "overcast": "阴天",
        "rain": "雨天", "heavy_rain": "暴雨", "snow": "雪天",
        "fog": "雾气弥漫", "storm": "风暴", "windy": "大风",
        "hot": "炎热", "cold": "寒冷"
    }
    
    if atmosphere.time_of_day != "unspecified":
        segments.append(f"当前时间: {time_names.get(atmosphere.time_of_day, atmosphere.time_of_day)}")
    
    if atmosphere.weather != "unspecified":
        segments.append(f"天气状况: {weather_names.get(atmosphere.weather, atmosphere.weather)}")
    
    if atmosphere.mood:
        segments.append(f"场景氛围: {atmosphere.mood}")
    
    if atmosphere.lighting:
        segments.append(f"光线: {atmosphere.lighting}")
    
    # 五感描写提示
    sensory = atmosphere.sensory_details
    sensory_hints = []
    if sensory.visual:
        sensory_hints.append(f"视觉: {', '.join(sensory.visual[:3])}")
    if sensory.auditory:
        sensory_hints.append(f"听觉: {', '.join(sensory.auditory[:3])}")
    if sensory.olfactory:
        sensory_hints.append(f"嗅觉: {', '.join(sensory.olfactory[:3])}")
    if sensory.tactile:
        sensory_hints.append(f"触觉: {', '.join(sensory.tactile[:3])}")
    
    if sensory_hints:
        segments.append("五感细节提示:\n  " + "\n  ".join(sensory_hints))
    
    if atmosphere.ambient_sounds:
        segments.append(f"环境音: {', '.join(atmosphere.ambient_sounds[:3])}")
    
    if atmosphere.special_effects:
        segments.append(f"特效: {', '.join(atmosphere.special_effects[:2])}")
    
    return "\n".join(segments)


def get_speech_pattern_description(speech: SpeechPattern) -> str:
    """
    根据语音特征生成描述
    """
    parts = []
    
    if speech.speaking_style:
        parts.append(f"说话风格{speech.speaking_style}")
    
    if speech.accent:
        parts.append(f"带有{speech.accent}")
    
    if speech.verbal_tics:
        parts.append(f"口头禅包括「{'」「'.join(speech.verbal_tics[:3])}」")
    
    vocab_desc = {
        "simple": "用词简单直接",
        "normal": "用词正常",
        "scholarly": "用词文雅",
        "archaic": "用词古风"
    }
    if speech.vocabulary_level in vocab_desc and speech.vocabulary_level != "normal":
        parts.append(vocab_desc[speech.vocabulary_level])
    
    if speech.emotional_expression:
        parts.append(f"情感表达{speech.emotional_expression}")
    
    if speech.speech_examples:
        parts.append(f"典型台词示例: 「{'」「'.join(speech.speech_examples[:2])}」")
    
    return "，".join(parts) if parts else ""


def get_dialogue_enhancement_prompt(enhancement: DialogueEnhancement) -> str:
    """
    生成对话增强 prompt 片段
    """
    hints = []
    
    if enhancement.enable_subtext:
        hints.append("对话中适当加入潜台词，让角色言外之意丰富")
    
    if enhancement.enable_body_language:
        hints.append("穿插肢体语言和微表情描写")
    
    if enhancement.enable_internal_thoughts:
        hints.append("适时展现角色内心独白")
    
    pacing_desc = {
        "rapid": "对话节奏快速，短句交锋",
        "balanced": "对话节奏平衡，张弛有度",
        "deliberate": "对话节奏沉稳，深思熟虑"
    }
    hints.append(pacing_desc.get(enhancement.dialogue_pacing, ""))
    
    if enhancement.tension_level >= 7:
        hints.append("对话中保持高张力，暗流涌动")
    elif enhancement.tension_level <= 3:
        hints.append("对话氛围轻松自然")
    
    return "\n".join(f"- {h}" for h in hints if h)
