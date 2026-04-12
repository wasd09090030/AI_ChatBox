"""实体 patch 结构化抽取服务。"""

from __future__ import annotations

import json
from typing import Any, Iterable, Optional

from models.entity_state import EntityStateSnapshot
from models.entity_state_event import EntityPatchExtractionResult
from .entity_patch_prompt import build_entity_patch_extraction_prompt


class EntityPatchExtractor:
    """负责调用 LLM 抽取结构化实体 patch。"""

    def build_prompt(
        self,
        *,
        user_input: str,
        generated_text: str,
        current_states: Iterable[EntityStateSnapshot],
    ) -> str:
        """功能：构建 prompt。"""
        return build_entity_patch_extraction_prompt(
            user_input=user_input,
            generated_text=generated_text,
            current_entity_states=[item.model_dump(mode="json") for item in current_states],
        )

    async def extract_async(
        self,
        *,
        llm: Any,
        user_input: str,
        generated_text: str,
        current_states: Iterable[EntityStateSnapshot],
    ) -> EntityPatchExtractionResult:
        """功能：处理 extract async。"""
        prompt = self.build_prompt(
            user_input=user_input,
            generated_text=generated_text,
            current_states=current_states,
        )
        response = await llm.ainvoke(prompt)
        return self._parse_result(getattr(response, "content", response))

    def extract_sync(
        self,
        *,
        llm: Any,
        user_input: str,
        generated_text: str,
        current_states: Iterable[EntityStateSnapshot],
    ) -> EntityPatchExtractionResult:
        """功能：处理 extract sync。"""
        prompt = self.build_prompt(
            user_input=user_input,
            generated_text=generated_text,
            current_states=current_states,
        )
        response = llm.invoke(prompt)
        return self._parse_result(getattr(response, "content", response))

    def _parse_result(self, raw_content: Any) -> EntityPatchExtractionResult:
        """功能：解析 result。"""
        text = str(raw_content or "").strip()
        if not text:
            return EntityPatchExtractionResult(warnings=["entity_patch extractor returned empty content"])

        normalized = self._strip_markdown_fence(text)
        try:
            payload = json.loads(normalized)
        except json.JSONDecodeError:
            return EntityPatchExtractionResult(warnings=["entity_patch extractor returned invalid json"])

        if not isinstance(payload, dict):
            return EntityPatchExtractionResult(warnings=["entity_patch extractor returned non-object payload"])

        try:
            return EntityPatchExtractionResult(**payload)
        except Exception as exc:
            return EntityPatchExtractionResult(warnings=[f"entity_patch extractor payload validation failed: {exc}"])

    @staticmethod
    def _strip_markdown_fence(text: str) -> str:
        """功能：处理 strip markdown fence。"""
        stripped = text.strip()
        if stripped.startswith("```") and stripped.endswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3:
                return "\n".join(lines[1:-1]).strip()
        return stripped
