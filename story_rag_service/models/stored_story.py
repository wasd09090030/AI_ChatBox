"""
Story Persistence Models
用于故事持久化的数据模型
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
import uuid

from models.story_runtime import ScriptRuntimeState


class StorySegment(BaseModel):
    """故事片段"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str = Field(..., description="用户输入的提示词")
    creation_mode: Optional[Literal["improv", "scripted"]] = Field(
        default=None,
        description="该轮输入所属的创作模式",
    )
    content: str = Field(..., description="AI生成的故事内容")
    retrieved_context: List[str] = Field(default_factory=list, description="使用的设定")
    runtime_state_snapshot: Optional[Dict[str, Any]] = Field(default=None, description="该片段生成完成后的运行态快照")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class StoredStory(BaseModel):
    """存储的故事"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    world_id: str = Field(..., description="所属世界ID")
    world_name: str = Field(..., description="世界名称(冗余,便于显示)")
    title: str = Field(default="未命名故事", description="故事标题")
    segments: List[StorySegment] = Field(default_factory=list, description="故事片段列表")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class StoryCreate(BaseModel):
    """创建故事请求"""
    world_id: str
    title: str = "未命名故事"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StoryUpdate(BaseModel):
    """更新故事请求"""
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class StoryProgressUpdate(BaseModel):
    """显式更新故事当前剧本推进状态"""
    script_design_id: Optional[str] = None
    active_stage_id: Optional[str] = None
    active_event_id: Optional[str] = None
    follow_script_design: Optional[bool] = None
    creation_mode: Optional[str] = None
    runtime_state_id: Optional[str] = None


class StorySegmentCreate(BaseModel):
    """添加故事片段请求"""
    prompt: str
    creation_mode: Optional[Literal["improv", "scripted"]] = None
    content: str
    retrieved_context: List[str] = Field(default_factory=list)
    runtime_state_snapshot: Optional[Dict[str, Any]] = None


class StorySegmentRollbackResponse(BaseModel):
    """删除最后一段故事并回退运行态后的响应。"""

    story: StoredStory
    runtime_state: Optional[ScriptRuntimeState] = None
    session_id: Optional[str] = None
    rebuild_summary_reset: bool = False
    rebuild_history_reindexed: bool = False
    rebuild_entity_state_rebuilt: bool = False
    memory_updates: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class StorySegmentContentUpdate(BaseModel):
    """更新已存在故事片段内容"""
    segment_id: str
    content: str


class StoryAdjustmentCommitRequest(BaseModel):
    """提交故事调整草稿"""
    session_id: Optional[str] = None
    updates: List[StorySegmentContentUpdate] = Field(default_factory=list)


class StoryAdjustmentCommitResponse(BaseModel):
    """故事调整提交结果"""
    story: StoredStory
    session_id: str
    rebuild_summary_reset: bool = False
    rebuild_history_reindexed: bool = False
    rebuild_entity_state_rebuilt: bool = False
    memory_updates: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
