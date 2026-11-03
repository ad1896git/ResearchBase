"""Project record listings, keyword search and short-number references."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any
from uuid import UUID

from researchbase.foundation.errors import ErrorCode, ResearchBaseError

_HEX_PREFIX = re.compile(r"^[0-9a-fA-F-]{6,36}$")


def _chinese_kind(kind: str) -> str:
    return {
        "question": "研究问题",
        "hypothesis": "假设",
        "experiment": "实验",
        "run": "运行",
        "claim": "结论",
        "paper": "文献",
        "evidence": "文献证据",
    }.get(kind, kind)


class RecordListingService:
    """Read-only. Short numbers are positions by creation time within a project and kind."""

    def __init__(self, uow_factory: Callable[[], Any]) -> None:
        self._uow_factory = uow_factory

    def list(self, project: UUID, kind: str, keyword: str | None = None) -> list[dict]:
        with self._uow_factory() as uow:
            rows = uow.record_listing.rows(kind, project)
        numbered = [{"short_no": n, "kind": kind, **row} for n, row in enumerate(rows, 1)]
        if keyword:
            needle = keyword.casefold()
            numbered = [r for r in numbered if needle in str(r.get("title") or "").casefold()]
        return numbered

    def paper_detail(self, source: UUID, project: UUID) -> dict | None:
        with self._uow_factory() as uow:
            return uow.record_listing.paper_detail(source, project)

    def resolve(self, project: UUID, kind: str, token: str) -> dict:
        """Accept a short number, UUID or UUID prefix, or (papers) a unique title fragment."""
        label = _chinese_kind(kind)
        text = token.strip()
        rows = self.list(project, kind)
        if text.isdigit():
            number = int(text)
            for row in rows:
                if row["short_no"] == number:
                    return row
            raise ResearchBaseError(
                ErrorCode.NOT_FOUND,
                f"没有编号为 {number} 的{label}",
                details={"kind": kind, "short_no": number, "available": len(rows)},
            )
        if _HEX_PREFIX.match(text):
            matches = [r for r in rows if str(r["id"]).startswith(text.lower())]
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                raise ResearchBaseError(
                    ErrorCode.VALIDATION_ERROR,
                    f"ID 前缀 {text} 对应多个{label}，请输入更长的前缀或使用编号",
                    details={"kind": kind, "matches": len(matches)},
                )
        if kind == "paper":
            matches = [r for r in rows if text.casefold() in str(r.get("title") or "").casefold()]
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                raise ResearchBaseError(
                    ErrorCode.VALIDATION_ERROR,
                    f"“{text}” 同时匹配 {len(matches)} 篇文献，请改用编号",
                    details={"kind": kind, "matches": len(matches)},
                )
        raise ResearchBaseError(
            ErrorCode.NOT_FOUND,
            f"找不到{label}“{text}”",
            details={"kind": kind},
        )
