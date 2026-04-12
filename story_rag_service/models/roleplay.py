"""角色扮演域模型。"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class PersonaProfile(BaseModel):
    """人格卡实体模型。"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1)
    description: str = ""
    title: Optional[str] = None
    traits: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PersonaProfileCreate(BaseModel):
    """新建人格卡请求模型。"""
    name: str = Field(..., min_length=1)
    description: str = ""
    title: Optional[str] = None
    traits: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PersonaProfileUpdate(BaseModel):
    """更新人格卡请求模型（支持局部更新）。"""
    name: Optional[str] = None
    description: Optional[str] = None
    title: Optional[str] = None
    traits: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class StoryState(BaseModel):
    """会话级剧情状态快照。"""
    session_id: str
    chapter: Optional[str] = None
    objective: Optional[str] = None
    conflict: Optional[str] = None
    clues: List[str] = Field(default_factory=list)
    relationship_arcs: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=datetime.now)


class StoryStateUpdate(BaseModel):
    """剧情状态更新请求模型（支持局部更新）。"""
    chapter: Optional[str] = None
    objective: Optional[str] = None
    conflict: Optional[str] = None
    clues: Optional[List[str]] = None
    relationship_arcs: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None
