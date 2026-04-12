"""
Data models for Story RAG Service
"""

from .lorebook import LorebookEntry, LorebookType, Character, Location, Event
from .entity_state import EntityStateSnapshot, EntityStateCollection, EntityStateRebuildResponse
from .entity_state_event import (
    EntityStateEventRecord,
    EntityStatePatch,
    EntityPatchApplyResult,
    EntityPatchExtractionResult,
)
from .story import StoryContext, StoryGenerationRequest, StoryGenerationResponse

# 控制 import * 时可导出的公共符号。
__all__ = [
    'LorebookEntry',
    'LorebookType',
    'Character',
    'Location',
    'Event',
    'EntityStateSnapshot',
    'EntityStateCollection',
    'EntityStateRebuildResponse',
    'EntityStateEventRecord',
    'EntityStatePatch',
    'EntityPatchApplyResult',
    'EntityPatchExtractionResult',
    'StoryContext',
    'StoryGenerationRequest',
    'StoryGenerationResponse',
]
