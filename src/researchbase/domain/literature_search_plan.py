"""Canonical, typed material for versioned literature search plans."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from researchbase.foundation.frozen_json import freeze_json, thaw_json
from researchbase.foundation.hashing import ContentHash, sha256_canonical_json


class LiteratureSourceScope(StrEnum):
    BIBLIOGRAPHIC = "BIBLIOGRAPHIC"
    WEB = "WEB"
    LOCAL_CORPUS = "LOCAL_CORPUS"
    MIXED = "MIXED"


class LiteratureSearchStrategy(StrEnum):
    KEYWORD = "KEYWORD"
    PERSPECTIVE_GUIDED = "PERSPECTIVE_GUIDED"
    SYSTEMATIC = "SYSTEMATIC"
    SNOWBALL = "SNOWBALL"
    HYBRID = "HYBRID"


class LiteratureSearchPlanStatus(StrEnum):
    DRAFT = "DRAFT"
    FROZEN = "FROZEN"
    SUPERSEDED = "SUPERSEDED"
    ABANDONED = "ABANDONED"


def canonical_language_identifier(raw: str) -> str:
    """Canonicalize an opaque language label without imposing a taxonomy."""
    if not isinstance(raw, str):
        raise TypeError("language identifier must be text")
    value = unicodedata.normalize("NFC", raw.strip())
    if not value:
        raise ValueError("language identifier must not be blank")
    return value


@dataclass(frozen=True, slots=True)
class FrozenResearchQuestionReference:
    research_question_id: UUID
    version_id: UUID
    content_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.research_question_id, UUID) or not isinstance(self.version_id, UUID):
            raise TypeError("ResearchQuestion and version IDs must be UUIDs")
        object.__setattr__(self, "content_hash", ContentHash(self.content_hash))

    def payload(self) -> dict[str, str]:
        return {
            "type": "ResearchQuestionVersion",
            "id": str(self.version_id),
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class LiteratureSearchPlanMaterial:
    plan_id: UUID
    research_question_refs: tuple[FrozenResearchQuestionReference, ...]
    objective: str
    source_scope: LiteratureSourceScope
    inclusion_criteria: Mapping[str, Any] | None
    exclusion_criteria: Mapping[str, Any] | None
    time_range: Mapping[str, date | None] | None
    language_scope: tuple[str, ...] | None
    search_strategy: LiteratureSearchStrategy
    planned_providers: tuple[str, ...]
    stopping_rule: Mapping[str, str] | None

    def __post_init__(self) -> None:
        if not isinstance(self.plan_id, UUID):
            raise TypeError("plan_id must be a UUID")
        object.__setattr__(self, "source_scope", LiteratureSourceScope(self.source_scope))
        object.__setattr__(self, "search_strategy", LiteratureSearchStrategy(self.search_strategy))
        object.__setattr__(self, "objective", _text(self.objective, "objective", nonblank=True))

        refs = tuple(self.research_question_refs)
        if any(not isinstance(ref, FrozenResearchQuestionReference) for ref in refs):
            raise TypeError("research_question_refs must contain typed frozen references")
        identities = [ref.research_question_id for ref in refs]
        if len(set(identities)) != len(identities):
            raise ValueError("duplicate ResearchQuestion identity")
        object.__setattr__(self, "research_question_refs", refs)

        for field_name, validator in (
            ("inclusion_criteria", _criteria),
            ("exclusion_criteria", _criteria),
        ):
            value = validator(getattr(self, field_name), field_name)
            object.__setattr__(self, field_name, freeze_json(value) if value is not None else None)
        time_range = _time_range(self.time_range)
        stopping_rule = _stopping_rule(self.stopping_rule)
        object.__setattr__(self, "time_range", freeze_json(time_range) if time_range else None)
        object.__setattr__(
            self, "stopping_rule", freeze_json(stopping_rule) if stopping_rule else None
        )

        if self.language_scope is not None:
            languages = tuple(canonical_language_identifier(raw) for raw in self.language_scope)
            if len(set(languages)) != len(languages):
                raise ValueError("duplicate canonical language identifier")
            object.__setattr__(self, "language_scope", tuple(sorted(languages)))

        providers = tuple(
            _text(value, "planned provider", trim=True, nonblank=True)
            for value in self.planned_providers
        )
        if len(set(providers)) != len(providers):
            raise ValueError("duplicate canonical planned provider")
        object.__setattr__(self, "planned_providers", tuple(sorted(providers)))

    def payload(self) -> dict[str, Any]:
        if self.language_scope is None:
            raise ValueError("language_scope must be non-NULL in frozen hash material")
        refs = sorted(
            (ref.payload() for ref in self.research_question_refs),
            key=lambda ref: (ref["type"], ref["id"], ref["content_hash"]),
        )
        return {
            "type": "LiteratureSearchPlanVersion",
            "material_version": 1,
            "plan_id": str(self.plan_id),
            "research_question_refs": refs,
            "objective": self.objective,
            "source_scope": self.source_scope.value,
            "inclusion_criteria": thaw_json(self.inclusion_criteria)
            if self.inclusion_criteria is not None
            else None,
            "exclusion_criteria": thaw_json(self.exclusion_criteria)
            if self.exclusion_criteria is not None
            else None,
            "time_range": thaw_json(self.time_range) if self.time_range is not None else None,
            "language_scope": list(self.language_scope),
            "search_strategy": self.search_strategy.value,
            "planned_providers": list(self.planned_providers),
            "stopping_rule": thaw_json(self.stopping_rule)
            if self.stopping_rule is not None
            else None,
        }

    def digest(self) -> str:
        return str(sha256_canonical_json(self.payload()))


def _text(value: str, field: str, *, trim: bool = False, nonblank: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be text")
    result = unicodedata.normalize("NFC", value.strip() if trim else value)
    if nonblank and not result.strip():
        raise ValueError(f"{field} must not be blank")
    if any(unicodedata.category(char) in {"Cc", "Cs"} for char in result):
        raise ValueError(f"{field} cannot contain controls or surrogates")
    return result


def _criteria(value: Mapping[str, Any] | None, field: str) -> dict[str, list[str]] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping) or set(value) != {"statements"}:
        raise ValueError(f"{field} must contain exactly statements")
    statements = value["statements"]
    if not isinstance(statements, list | tuple):
        raise ValueError(f"{field}.statements must be a sequence")
    normalized = [_text(item, f"{field} statement", nonblank=True) for item in statements]
    return {"statements": normalized}


def _time_range(value: Mapping[str, date | None] | None) -> dict[str, str | None] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping) or set(value) != {"from", "through"}:
        raise ValueError("time_range must contain exactly from and through")
    start, end = value["from"], value["through"]
    for bound in (start, end):
        if bound is not None and (not isinstance(bound, date) or isinstance(bound, datetime)):
            raise TypeError("time_range bounds must be dates or null")
    if start is None and end is None:
        raise ValueError("time_range requires at least one bound")
    if start is not None and end is not None and start > end:
        raise ValueError("time_range from must not exceed through")
    return {
        "from": start.isoformat() if start is not None else None,
        "through": end.isoformat() if end is not None else None,
    }


def _stopping_rule(value: Mapping[str, str] | None) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping) or set(value) != {"rule"}:
        raise ValueError("stopping_rule must contain exactly rule")
    return {"rule": _text(value["rule"], "stopping_rule.rule", nonblank=True)}
