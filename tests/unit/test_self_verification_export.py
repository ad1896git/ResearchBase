"""Owner self-verification is shown in the Markdown export (no database)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from researchbase.cli.markdown_export import render

PROJECT = UUID("835c1e6e-a1b5-49fb-b452-39c2485eb00f")


def _paper_rows(evidence_self_verified: bool | None) -> dict[str, list[dict]]:
    paper = UUID("01a1a100-0000-7000-8000-000000000001")
    paper_version = UUID("01a1a100-0000-7000-8000-000000000002")
    evidence = UUID("01a1a100-0000-7000-8000-000000000003")
    return {
        "paper": [
            {
                "id": paper,
                "short_no": 1,
                "title": "虚构文献",
                "status": "ACTIVE",
                "version_id": str(paper_version),
            }
        ],
        "evidence": [
            {
                "id": evidence,
                "short_no": 1,
                "title": "午睡组得分更高",
                "status": "VERIFIED",
                "parent_id": str(paper_version),
                "self_verified": evidence_self_verified,
            }
        ],
    }


def test_self_verified_evidence_is_marked_in_the_citation_list():
    text = render(str(PROJECT), _paper_rows(True), [], datetime(2026, 11, 3, 9, 0))
    assert "引文 #1：「午睡组得分更高」（本人核验）" in text


def test_evidence_verified_by_someone_else_has_no_mark():
    text = render(str(PROJECT), _paper_rows(False), [], datetime(2026, 11, 3, 9, 0))
    assert "引文 #1：「午睡组得分更高」" in text
    assert "本人核验" not in text
