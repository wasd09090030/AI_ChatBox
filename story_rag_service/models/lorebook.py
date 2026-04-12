"""知识库条目数据模型。"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from datetime import datetime


class LorebookType(str, Enum):
    """知识库条目类型。"""
    WORLD_SETTING = "world_setting"  # 世界设定
    CHARACTER = "character"
    LOCATION = "location"
    EVENT = "event"
    ITEM = "item"
    FACTION = "faction"
    LORE = "lore"
    CUSTOM = "custom"
    CONVERSATION_HISTORY = "conversation_history"  # 历史消息


class LorebookEntry(BaseModel):
    """知识库基础条目。"""
    id: Optional[str] = None
    world_id: str = Field(..., description="ID of the world this entry belongs to")
    type: LorebookType
    name: str = Field(..., description="Name of the entry (e.g., character name, location name)")
    description: str = Field(..., description="Detailed description of the entry")
    keywords: List[str] = Field(default_factory=list, description="Keywords to trigger this entry")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        """作用：定义配置读取规则与环境变量加载行为。"""
        use_enum_values = True


class Character(BaseModel):
    """角色类 lorebook 条目。"""
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    appearance: Optional[str] = None
    personality: Optional[str] = None
    background: Optional[str] = None
    relationships: Dict[str, str] = Field(default_factory=dict, description="Relationships with other characters")
    abilities: List[str] = Field(default_factory=list)
    inventory: List[str] = Field(default_factory=list)
    current_location: Optional[str] = None
    
    # 对话增强 - 语音特征
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
    emotional_expression: Optional[str] = Field(
        default=None,
        description="情感表达方式，如'内敛含蓄'、'热情奔放'、'面无表情'"
    )
    speech_examples: List[str] = Field(
        default_factory=list,
        description="台词示例，展示角色的说话方式"
    )
    role_tier: Literal["npc", "principal"] = Field(
        default="npc",
        description="角色层级：npc=普通设定角色，principal=关键角色"
    )
    dialogue_enabled: bool = Field(
        default=False,
        description="是否允许在故事创作中作为重点对白角色使用"
    )
    opening_line: Optional[str] = Field(
        default=None,
        description="关键角色的建议开场白"
    )
    example_dialogues: List[str] = Field(
        default_factory=list,
        description="关键角色对白示例"
    )
    story_function: Optional[str] = Field(
        default=None,
        description="角色在剧情中的功能定位"
    )
    
    def to_lorebook_entry(self, world_id: str) -> LorebookEntry:
        """转换为通用 LorebookEntry。"""
        description_parts = [
            f"姓名: {self.name}",
        ]
        
        if self.age:
            description_parts.append(f"年龄: {self.age}")
        if self.gender:
            description_parts.append(f"性别: {self.gender}")
        if self.appearance:
            description_parts.append(f"外貌: {self.appearance}")
        if self.personality:
            description_parts.append(f"性格: {self.personality}")
        if self.background:
            description_parts.append(f"背景: {self.background}")
        if self.relationships:
            rel_text = ", ".join([f"{k}({v})" for k, v in self.relationships.items()])
            description_parts.append(f"关系: {rel_text}")
        if self.abilities:
            description_parts.append(f"能力: {', '.join(self.abilities)}")
        if self.current_location:
            description_parts.append(f"当前位置: {self.current_location}")
        
        # 语音特征描述
        speech_parts = []
        if self.speaking_style:
            speech_parts.append(f"说话风格{self.speaking_style}")
        if self.accent:
            speech_parts.append(f"带有{self.accent}")
        if self.verbal_tics:
            speech_parts.append(f"口头禅「{'\u300d\u300c'.join(self.verbal_tics[:3])}\u300d")
        if self.vocabulary_level and self.vocabulary_level != "normal":
            vocab_desc = {"simple": "用词简单直接", "scholarly": "用词文雅", "archaic": "用词古风"}
            speech_parts.append(vocab_desc.get(self.vocabulary_level, ""))
        if self.emotional_expression:
            speech_parts.append(f"情感表达{self.emotional_expression}")
        if speech_parts:
            description_parts.append(f"语音特征: {'，'.join(speech_parts)}")
        if self.speech_examples:
            description_parts.append(f"台词示例: \u300c{'\u300d\u300c'.join(self.speech_examples[:2])}\u300d")
        if self.role_tier == "principal":
            description_parts.append("角色定位: 关键角色")
        if self.story_function:
            description_parts.append(f"剧情功能: {self.story_function}")
        if self.dialogue_enabled:
            description_parts.append("对白能力: 允许在故事创作中作为重点交流对象")
        if self.opening_line:
            description_parts.append(f"建议开场白: {self.opening_line}")
        if self.example_dialogues:
            description_parts.append(f"对白示例: \u300c{'\u300d\u300c'.join(self.example_dialogues[:2])}\u300d")
        
        return LorebookEntry(
            world_id=world_id,
            type=LorebookType.CHARACTER,
            name=self.name,
            description="\n".join(description_parts),
            keywords=[self.name] + list(self.relationships.keys()),
            metadata=self.model_dump()
        )


class Location(BaseModel):
    """地点类 lorebook 条目。"""
    name: str
    description: str
    region: Optional[str] = None
    climate: Optional[str] = None
    population: Optional[int] = None
    notable_features: List[str] = Field(default_factory=list)
    connected_locations: List[str] = Field(default_factory=list)
    inhabitants: List[str] = Field(default_factory=list, description="Notable inhabitants")
    
    # 场景氛围增强
    default_time_of_day: Optional[str] = Field(
        default=None,
        description="典型时间: dawn, morning, noon, afternoon, dusk, evening, night, midnight"
    )
    default_weather: Optional[str] = Field(
        default=None,
        description="典型天气: clear, cloudy, rain, snow, fog, storm"
    )
    mood: Optional[str] = Field(
        default=None,
        description="场景情绪氛围，如'紧张'、'祥和'、'诡异'、'浪漫'"
    )
    lighting: Optional[str] = Field(
        default=None,
        description="光线描述，如'昏暗'、'明亮'、'烛光摇曳'"
    )
    
    # 五感描写
    sensory_visual: List[str] = Field(
        default_factory=list,
        description="视觉描写元素，如['昏暗的烛光', '斑驳的墙壁']"
    )
    sensory_auditory: List[str] = Field(
        default_factory=list,
        description="听觉描写元素，如['远处的钟声', '风声呼啸']"
    )
    sensory_olfactory: List[str] = Field(
        default_factory=list,
        description="嗅觉描写元素，如['潮湿的泥土味', '花香']"
    )
    sensory_tactile: List[str] = Field(
        default_factory=list,
        description="触觉描写元素，如['冰冷的石壁', '粗糙的树皮']"
    )
    ambient_sounds: List[str] = Field(
        default_factory=list,
        description="环境背景音，如['蝉鸣', '流水声']"
    )
    special_effects: List[str] = Field(
        default_factory=list,
        description="特殊效果，如['魔法光芒', '迷雾弥漫']"
    )
    
    def to_lorebook_entry(self, world_id: str) -> LorebookEntry:
        """转换为通用 LorebookEntry。"""
        description_parts = [
            f"地点名称: {self.name}",
            f"描述: {self.description}",
        ]
        
        if self.region:
            description_parts.append(f"所属区域: {self.region}")
        if self.climate:
            description_parts.append(f"气候: {self.climate}")
        if self.population:
            description_parts.append(f"人口: {self.population}")
        if self.notable_features:
            description_parts.append(f"特色: {', '.join(self.notable_features)}")
        if self.connected_locations:
            description_parts.append(f"相连地点: {', '.join(self.connected_locations)}")
        if self.inhabitants:
            description_parts.append(f"重要居民: {', '.join(self.inhabitants)}")
        
        # 场景氛围描写
        atmosphere_parts = []
        time_names = {
            "dawn": "黎明", "morning": "清晨", "noon": "正午",
            "afternoon": "下午", "dusk": "黄昏", "evening": "傍晚",
            "night": "夜晚", "midnight": "深夜"
        }
        weather_names = {
            "clear": "晴朗", "cloudy": "多云", "overcast": "阴天",
            "rain": "雨天", "snow": "雪天", "fog": "雾气弥漫", "storm": "风暴"
        }
        if self.default_time_of_day:
            atmosphere_parts.append(f"典型时间: {time_names.get(self.default_time_of_day, self.default_time_of_day)}")
        if self.default_weather:
            atmosphere_parts.append(f"典型天气: {weather_names.get(self.default_weather, self.default_weather)}")
        if self.mood:
            atmosphere_parts.append(f"氛围: {self.mood}")
        if self.lighting:
            atmosphere_parts.append(f"光线: {self.lighting}")
        if atmosphere_parts:
            description_parts.append("【场景氛围】\n" + "\n".join(atmosphere_parts))
        
        # 五感描写
        sensory_parts = []
        if self.sensory_visual:
            sensory_parts.append(f"视觉: {', '.join(self.sensory_visual[:3])}")
        if self.sensory_auditory:
            sensory_parts.append(f"听觉: {', '.join(self.sensory_auditory[:3])}")
        if self.sensory_olfactory:
            sensory_parts.append(f"嗅觉: {', '.join(self.sensory_olfactory[:3])}")
        if self.sensory_tactile:
            sensory_parts.append(f"触觉: {', '.join(self.sensory_tactile[:3])}")
        if self.ambient_sounds:
            sensory_parts.append(f"环境音: {', '.join(self.ambient_sounds[:3])}")
        if self.special_effects:
            sensory_parts.append(f"特效: {', '.join(self.special_effects[:2])}")
        if sensory_parts:
            description_parts.append("【五感细节】\n" + "\n".join(sensory_parts))
        
        keywords = [self.name]
        if self.region:
            keywords.append(self.region)
        keywords.extend(self.connected_locations)
        
        return LorebookEntry(
            world_id=world_id,
            type=LorebookType.LOCATION,
            name=self.name,
            description="\n".join(description_parts),
            keywords=keywords,
            metadata=self.model_dump()
        )


class Event(BaseModel):
    """事件类 lorebook 条目。"""
    name: str
    description: str
    time: Optional[str] = None
    location: Optional[str] = None
    participants: List[str] = Field(default_factory=list)
    consequences: Optional[str] = None
    importance: int = Field(default=5, ge=1, le=10, description="Event importance (1-10)")
    
    def to_lorebook_entry(self, world_id: str) -> LorebookEntry:
        """转换为通用 LorebookEntry。"""
        description_parts = [
            f"事件名称: {self.name}",
            f"描述: {self.description}",
        ]
        
        if self.time:
            description_parts.append(f"时间: {self.time}")
        if self.location:
            description_parts.append(f"地点: {self.location}")
        if self.participants:
            description_parts.append(f"参与者: {', '.join(self.participants)}")
        if self.consequences:
            description_parts.append(f"影响: {self.consequences}")
        
        keywords = [self.name]
        if self.location:
            keywords.append(self.location)
        keywords.extend(self.participants)
        
        return LorebookEntry(
            world_id=world_id,
            type=LorebookType.EVENT,
            name=self.name,
            description="\n".join(description_parts),
            keywords=keywords,
            metadata=self.model_dump()
        )
