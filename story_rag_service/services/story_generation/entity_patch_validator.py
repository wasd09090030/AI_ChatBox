"""实体 patch 校验与归一化服务。"""

from __future__ import annotations

from typing import Any, Dict

from models.entity_state_event import EntityPatchExtractionResult, EntityStatePatch


class EntityPatchValidator:
    """校验 patch 的引用合法性与字段操作合法性。"""

    _LIST_FIELDS = {"inventory", "status_tags", "companions"}
    _SCALAR_FIELDS = {"current_location", "short_goal", "state_summary"}

    def validate(
        self,
        *,
        extraction: EntityPatchExtractionResult,
        character_lookup: Dict[str, Dict],
        location_lookup: Dict[str, Dict],
    ) -> EntityPatchExtractionResult:
        warnings = list(extraction.warnings)
        valid_patches: list[EntityStatePatch] = []

        character_id_lookup = {
            str(entry.get("id") or "").strip(): entry
            for entry in character_lookup.values()
            if str(entry.get("id") or "").strip()
        }
        valid_location_names = {name for name in location_lookup.keys() if name}

        for patch in extraction.patches:
            normalized_patch = patch.model_copy(deep=True)
            normalized_entity = self._resolve_character_entry(
                entity_id=normalized_patch.entity_id,
                entity_name=normalized_patch.entity_name,
                character_lookup=character_lookup,
                character_id_lookup=character_id_lookup,
            )
            if normalized_entity is None:
                warnings.append(f"unknown entity skipped: {patch.entity_id or patch.entity_name}")
                continue
            normalized_patch.entity_id = str(normalized_entity.get("id") or "").strip()
            normalized_patch.entity_name = (
                str(normalized_entity.get("name") or "").strip() or normalized_patch.entity_name
            )

            if normalized_patch.field_name in self._LIST_FIELDS and normalized_patch.op not in {"set", "add", "remove", "clear", "reset"}:
                warnings.append(f"invalid list op skipped: {normalized_patch.field_name}/{normalized_patch.op}")
                continue

            if normalized_patch.field_name in self._SCALAR_FIELDS and normalized_patch.op not in {"set", "clear", "reset"}:
                warnings.append(f"invalid scalar op skipped: {normalized_patch.field_name}/{normalized_patch.op}")
                continue

            if normalized_patch.field_name == "companions":
                normalized_patch.value = self._normalize_companions(
                    normalized_patch.value,
                    character_lookup=character_lookup,
                    character_id_lookup=character_id_lookup,
                )

            if normalized_patch.field_name == "current_location" and normalized_patch.op == "set":
                location_name = str(normalized_patch.value or "").strip()
                if valid_location_names and location_name and location_name not in valid_location_names:
                    warnings.append(f"unknown location skipped: {location_name}")
                    continue

            valid_patches.append(normalized_patch)

        return EntityPatchExtractionResult(
            patches=valid_patches,
            warnings=warnings,
        )

    @staticmethod
    def _resolve_character_entry(
        *,
        entity_id: str,
        entity_name: str | None,
        character_lookup: Dict[str, Dict],
        character_id_lookup: Dict[str, Dict],
    ) -> Dict[str, Any] | None:
        normalized_id = str(entity_id or "").strip()
        if normalized_id and normalized_id in character_id_lookup:
            return character_id_lookup[normalized_id]

        normalized_name = str(entity_name or "").strip()
        if normalized_name and normalized_name in character_lookup:
            return character_lookup[normalized_name]
        return None

    def _normalize_companions(
        self,
        value: Any,
        *,
        character_lookup: Dict[str, Dict],
        character_id_lookup: Dict[str, Dict],
    ) -> list[str]:
        raw_values = value if isinstance(value, list) else [value]
        normalized: list[str] = []
        for item in raw_values:
            text = str(item or "").strip()
            if not text:
                continue
            resolved = self._resolve_character_entry(
                entity_id=text,
                entity_name=text,
                character_lookup=character_lookup,
                character_id_lookup=character_id_lookup,
            )
            normalized_id = str((resolved or {}).get("id") or text).strip()
            if normalized_id and normalized_id not in normalized:
                normalized.append(normalized_id)
        return normalized
