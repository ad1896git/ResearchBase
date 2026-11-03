"""Unit tests for the terminal record flow helpers (no database)."""

from __future__ import annotations

from uuid import UUID

import pytest

from researchbase.application.record_listing import RecordListingService
from researchbase.cli.commands.experiment import normalized_run_type
from researchbase.cli.transport import _chinese_usage
from researchbase.foundation.errors import ResearchBaseError

PROJECT = UUID("835c1e6e-a1b5-49fb-b452-39c2485eb00f")
IDS = [
    UUID("01a19fd7-0000-7000-8000-000000000001"),
    UUID("01a19fd7-0000-7000-8000-000000000002"),
    UUID("01a1a03e-0000-7000-8000-000000000003"),
]


class _Repo:
    def __init__(self, rows):
        self._rows = rows

    def rows(self, kind, project):
        assert project == PROJECT
        return list(self._rows[kind])

    def paper_detail(self, source, project):
        return None


class _Uow:
    def __init__(self, rows):
        self.record_listing = _Repo(rows)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _service(rows):
    return RecordListingService(lambda: _Uow(rows))


def _rows():
    return {
        "question": [
            {"id": IDS[0], "title": "午睡是否改善记忆", "status": "FROZEN"},
            {"id": IDS[1], "title": "咖啡影响注意力", "status": "DRAFT"},
            {"id": IDS[2], "title": "午睡的时长", "status": "DRAFT"},
        ],
        "paper": [{"id": IDS[0], "title": "虚构文献：小睡与记忆", "status": "ACTIVE"}],
    }


def test_short_numbers_are_creation_order_positions():
    rows = _service(_rows()).list(PROJECT, "question")
    assert [row["short_no"] for row in rows] == [1, 2, 3]


def test_keyword_filters_by_title_and_keeps_short_numbers():
    rows = _service(_rows()).list(PROJECT, "question", keyword="午睡")
    assert [(row["short_no"], row["title"]) for row in rows] == [
        (1, "午睡是否改善记忆"),
        (3, "午睡的时长"),
    ]


def test_resolve_accepts_short_number_and_uuid_prefix():
    service = _service(_rows())
    assert service.resolve(PROJECT, "question", "2")["title"] == "咖啡影响注意力"
    assert service.resolve(PROJECT, "question", str(IDS[2])[:10])["short_no"] == 3


def test_resolve_missing_number_is_chinese_not_found():
    with pytest.raises(ResearchBaseError) as caught:
        _service(_rows()).resolve(PROJECT, "question", "9")
    assert caught.value.code.value == "NOT_FOUND"
    assert "没有编号为 9 的研究问题" in caught.value.message


def test_paper_can_be_named_by_unique_title_fragment():
    row = _service(_rows()).resolve(PROJECT, "paper", "小睡")
    assert row["id"] == IDS[0]


def test_ambiguous_uuid_prefix_is_rejected():
    rows = _rows()
    rows["question"][1]["id"] = UUID("01a19fd7-0000-7000-8000-00000000ffff")
    with pytest.raises(ResearchBaseError) as caught:
        _service(rows).resolve(PROJECT, "question", "01a19fd7")
    assert "多个研究问题" in caught.value.message


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("EXPERIMENT", "experiment"), (" pilot ", "pilot"), (None, None)],
)
def test_run_type_is_folded_to_lowercase_identifier(raw, expected):
    assert normalized_run_type(raw) == expected


@pytest.mark.parametrize("raw", ["中文", "two words", "1abc", "x" * 33])
def test_run_type_rejects_non_identifiers(raw):
    with pytest.raises(ResearchBaseError) as caught:
        normalized_run_type(raw)
    assert "英文字母" in str((caught.value.details or {}).get("reason", ""))


def test_usage_errors_are_translated_to_chinese():
    assert _chinese_usage("No such option: --bogus") == (
        "没有这个参数：--bogus。可运行 --help 查看用法"
    )
    assert _chinese_usage("Missing argument 'TEXT'.") == (
        "缺少必填位置参数：TEXT。可运行 --help 查看用法"
    )
    assert _chinese_usage("No such command 'nosuch'.") == (
        "没有这个命令：nosuch。可运行 --help 查看用法"
    )
    assert _chinese_usage("something else") == "something else"


def test_markdown_export_keeps_short_numbers_and_links():
    from datetime import datetime

    from researchbase.cli.markdown_export import render

    question = UUID("01a19fd7-0000-7000-8000-0000000000aa")
    hypothesis = UUID("01a19fd7-0000-7000-8000-0000000000bb")
    claim_version = UUID("01a19fd7-0000-7000-8000-0000000000cc")
    result = UUID("01a19fd7-0000-7000-8000-0000000000dd")
    rows = {
        "question": [{"id": question, "short_no": 1, "title": "问题", "status": "FROZEN"}],
        "hypothesis": [
            {
                "id": hypothesis,
                "short_no": 1,
                "title": "假设",
                "status": "FROZEN",
                "parent_id": str(question),
            }
        ],
        "result": [
            {"id": result, "short_no": 1, "title": "19 分", "status": "RECORDED", "parent_id": None}
        ],
        "claim": [
            {
                "id": UUID("01a19fd7-0000-7000-8000-0000000000ee"),
                "short_no": 1,
                "title": "结论",
                "status": "FROZEN",
                "version_id": str(claim_version),
            }
        ],
    }
    links = [
        {
            "claim_version_id": str(claim_version),
            "kind": "measurement",
            "target_id": str(result),
            "relation_type": "qualifies",
            "qualification": "说明",
        }
    ]
    text = render(str(PROJECT), rows, links, datetime(2026, 11, 3, 9, 30))
    assert "- **#1 问题**（已冻结）" in text
    assert "  - 假设 #1 假设（已冻结）" in text
    assert "- **#1 结论**（已冻结）" in text
    assert "限定：测量结果 #1 19 分；说明：说明" in text
    assert "1. " not in text.split("## 参考文献")[0]


def test_missing_text_outside_a_terminal_names_the_missing_field(monkeypatch):
    from researchbase.cli.commands.quick import _ask

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert _ask("  已有文字  ", "研究问题的文字") == "已有文字"
    with pytest.raises(ResearchBaseError) as caught:
        _ask(None, "研究问题的文字")
    assert "缺少研究问题的文字" in caught.value.message


def test_completion_is_silent_without_a_profile(monkeypatch):
    from researchbase.cli.commands import quick

    def broken_services():
        raise RuntimeError("no database")

    monkeypatch.setattr("researchbase.cli.composition.build_services", broken_services)
    assert quick._complete_kind("paper")("") == []
