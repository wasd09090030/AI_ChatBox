"""
v2 故事生成 LangGraph 工作流状态定义。
"""

from typing import Any, Dict, Optional, TypedDict
from models.story import StoryGenerationRequest, StoryGenerationResponse


class StoryGraphState(TypedDict, total=False):
    """故事图 v2 的共享状态对象。

    字段分层约定：
    - 输入层：`request_payload`、`thread_id`、`user_id`
    - 内部层：`internal_request`、`internal_response`、`story_state_snapshot`
    - 输出层：`v2_response`、`error`
    """

    request_payload: Dict[str, Any]
    thread_id: str
    user_id: Optional[str]

    internal_request: StoryGenerationRequest
    internal_response: StoryGenerationResponse
    story_state_snapshot: Dict[str, Any]
    v2_response: Dict[str, Any]
    error: str
