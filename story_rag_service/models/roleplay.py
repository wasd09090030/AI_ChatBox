"""
Roleplay domain models.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class PersonaProfile(BaseModel):
    """作用：定义 PersonaProfile 类型，承载本模块核心状态与行为。"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1)
    description: str = ""
    title: Optional[str] = None
    traits: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PersonaProfileCreate(BaseModel):
    """作用：定义 PersonaProfileCreate 类型，承载本模块核心状态与行为。"""
    name: str = Field(..., min_length=1)
    description: str = ""
    title: Optional[str] = None
    traits: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PersonaProfileUpdate(BaseModel):
    """作用：定义 PersonaProfileUpdate 类型，承载本模块核心状态与行为。"""
    name: Optional[str] = None
    description: Optional[str] = None
    title: Optional[str] = None
    traits: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class StoryState(BaseModel):
    """作用：定义 StoryState 数据结构，用于约束字段语义与序列化格式。"""
    session_id: str
    chapter: Optional[str] = None
    objective: Optional[str] = None
    conflict: Optional[str] = None
    clues: List[str] = Field(default_factory=list)
    relationship_arcs: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=datetime.now)


class StoryStateUpdate(BaseModel):
    """作用：定义 StoryStateUpdate 类型，承载本模块核心状态与行为。"""
    chapter: Optional[str] = None
    objective: Optional[str] = None
    conflict: Optional[str] = None
    clues: Optional[List[str]] = None
    relationship_arcs: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None
