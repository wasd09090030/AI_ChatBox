"""故事世界模型。"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid


class World(BaseModel):
    """故事世界实体。"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="World name", min_length=1)
    description: str = Field(..., description="World description")
    genre: Optional[str] = Field(default="fantasy", description="Story genre (fantasy, sci-fi, modern, etc.)")
    setting: Optional[str] = Field(default=None, description="Time period and location setting")
    rules: Optional[str] = Field(default=None, description="World rules (magic system, tech level, etc.)")
    
    # 风格模板配置
    style_preset: Optional[str] = Field(
        default=None, 
        description="预设风格模板: fantasy, wuxia, xianxia, noir, horror, romance, scifi, mystery, comedy, slice_of_life"
    )
    narrative_tone: Optional[str] = Field(
        default=None,
        description="叙事基调: light, dark, serious, humorous, mysterious, romantic, epic, intimate, tense"
    )
    pacing_style: Optional[str] = Field(
        default=None,
        description="叙事节奏: fast, moderate, slow, variable"
    )
    vocabulary_style: Optional[str] = Field(
        default=None,
        description="词汇风格描述，如'古风文言'、'现代口语'、'硬汉派简洁'"
    )
    style_tags: List[str] = Field(
        default_factory=list,
        description="风格标签，如['诗意', '血腥', '温馨']"
    )
    
    # 默认场景氛围
    default_time_of_day: Optional[str] = Field(
        default=None,
        description="默认时间: dawn, morning, noon, afternoon, dusk, evening, night, midnight"
    )
    default_weather: Optional[str] = Field(
        default=None,
        description="默认天气: clear, cloudy, overcast, rain, snow, fog, storm"
    )
    default_mood: Optional[str] = Field(
        default=None,
        description="默认氛围，如'神秘'、'温馨'、'紧张'"
    )
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        """作用：定义配置读取规则与环境变量加载行为。"""
        json_schema_extra = {
            "example": {
                "name": "修仙世界",
                "description": "一个充满仙气与灵力的东方玄幻世界",
                "genre": "xianxia",
                "setting": "古代东方大陆",
                "rules": "修炼者可以吸收天地灵气,分为炼气、筑基、金丹等境界"
            }
        }


class WorldCreate(BaseModel):
    """创建世界请求。"""
    name: str = Field(..., min_length=1)
    description: str
    genre: Optional[str] = "fantasy"
    setting: Optional[str] = None
    rules: Optional[str] = None
    
    # 风格配置
    style_preset: Optional[str] = None
    narrative_tone: Optional[str] = None
    pacing_style: Optional[str] = None
    vocabulary_style: Optional[str] = None
    style_tags: List[str] = Field(default_factory=list)
    
    # 默认氛围
    default_time_of_day: Optional[str] = None
    default_weather: Optional[str] = None
    default_mood: Optional[str] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorldUpdate(BaseModel):
    """更新世界请求。"""
    name: Optional[str] = None
    description: Optional[str] = None
    genre: Optional[str] = None
    setting: Optional[str] = None
    rules: Optional[str] = None
    
    # 风格配置
    style_preset: Optional[str] = None
    narrative_tone: Optional[str] = None
    pacing_style: Optional[str] = None
    vocabulary_style: Optional[str] = None
    style_tags: Optional[List[str]] = None
    
    # 默认氛围
    default_time_of_day: Optional[str] = None
    default_weather: Optional[str] = None
    default_mood: Optional[str] = None
    
    metadata: Optional[Dict[str, Any]] = None
