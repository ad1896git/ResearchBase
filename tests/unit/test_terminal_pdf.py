"""Unit tests for PDF text extraction used by `rb paper add` (no database)."""

from __future__ import annotations

from pathlib import Path

import pytest

from researchbase.cli.commands.quick import _doi_in, _pdf_text, _valid_doi
from researchbase.domain.source_identity import IdentifierType, normalize_source_identifier
from researchbase.foundation.errors import ResearchBaseError


def _minimal_pdf(lines: list[str]) -> bytes:
    """Build a small, valid one-page PDF whose text is the given lines."""

    content = (
        "BT /F1 12 Tf 72 720 Td " + " ".join(f"({line}) Tj 0 -16 Td" for line in lines) + " ET"
    )
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    body = "%PDF-1.4\n"
    offsets = []
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(body.encode()))
        body += f"{number} 0 obj\n{obj}\nendobj\n"
    xref = len(body.encode())
    body += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    body += "".join(f"{offset:010d} 00000 n \n" for offset in offsets)
    body += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return body.encode()


def test_pdf_text_and_doi_are_extracted(tmp_path: Path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(_minimal_pdf(["Nap and memory", "DOI 10.1234/nap.2026.7."]))
    text, properties = _pdf_text(pdf)
    assert "Nap and memory" in text
    assert _doi_in(text) == "10.1234/nap.2026.7"
    assert properties == {}


def test_doi_is_none_when_absent():
    assert _doi_in("no identifier here") is None


def test_valid_doi_is_stored_in_normalized_form():
    expected = normalize_source_identifier(
        IdentifierType.DOI, "10.1234/nap.2026.7"
    ).normalized_value
    assert _valid_doi("10.1234/nap.2026.7") == expected


def test_malformed_doi_is_dropped_instead_of_failing_the_import():
    assert _valid_doi("10.1234/bad%zz") is None


def test_missing_doi_stays_missing():
    assert _valid_doi(None) is None


def test_pdf_without_text_is_rejected_in_chinese(tmp_path: Path):
    pdf = tmp_path / "blank.pdf"
    pdf.write_bytes(_minimal_pdf([]))
    with pytest.raises(ResearchBaseError) as caught:
        _pdf_text(pdf)
    assert "没有可提取的文字" in caught.value.message


def test_broken_pdf_is_rejected_in_chinese(tmp_path: Path):
    pdf = tmp_path / "broken.pdf"
    pdf.write_bytes(b"not a pdf at all")
    with pytest.raises(ResearchBaseError) as caught:
        _pdf_text(pdf)
    assert "无法读取这个 PDF 文件" in caught.value.message


def test_known_doi_is_refused_before_any_write(monkeypatch):
    from uuid import uuid4

    from researchbase.cli.commands import quick
    from researchbase.foundation.errors import ErrorCode

    monkeypatch.setattr(quick, "_lo", lambda *args: {"title": "已有文献"})
    with pytest.raises(ResearchBaseError) as caught:
        quick._refuse_known_doi(uuid4(), "10.1234/nap.2026.7")
    assert caught.value.code is ErrorCode.DUPLICATE_CONTENT
    assert "已有文献" in str((caught.value.details or {}).get("reason", ""))


def test_unknown_doi_is_allowed_to_import(monkeypatch):
    from uuid import uuid4

    from researchbase.cli.commands import quick
    from researchbase.foundation.errors import ErrorCode

    def not_found(*args):
        raise ResearchBaseError(ErrorCode.SOURCE_NOT_FOUND, "source not found")

    monkeypatch.setattr(quick, "_lo", not_found)
    assert quick._refuse_known_doi(uuid4(), "10.1234/nap.2026.7") is None


def test_other_lookup_errors_are_not_swallowed(monkeypatch):
    from uuid import uuid4

    from researchbase.cli.commands import quick
    from researchbase.foundation.errors import ErrorCode

    def broken(*args):
        raise ResearchBaseError(ErrorCode.ADAPTER_UNAVAILABLE, "down")

    monkeypatch.setattr(quick, "_lo", broken)
    with pytest.raises(ResearchBaseError) as caught:
        quick._refuse_known_doi(uuid4(), "10.1234/nap.2026.7")
    assert caught.value.code is ErrorCode.ADAPTER_UNAVAILABLE


def test_crossref_date_needs_a_full_date():
    from researchbase.cli.commands.quick import _crossref_date

    assert _crossref_date({"published": {"date-parts": [[2013, 10, 24]]}}) == "2013-10-24"
    assert _crossref_date({"published": {"date-parts": [[2013]]}}) is None
    assert _crossref_date({}) is None


def test_paper_material_carries_crossref_fields():
    from researchbase.cli.commands.quick import _paper_material

    meta = {
        "authors": [{"name": "甲", "orcid": None}],
        "published": {"date-parts": [[2020, 2, 3]]},
        "venue": "期刊",
        "volume": 3,
        "pages": "1-9",
    }
    material = _paper_material("标题", {"artifact_version_id": "a", "content_hash": "h"}, meta)
    assert material["publication_date"] == "2020-02-03"
    assert material["venue"] == "期刊"
    assert material["authors"] == [{"name": "甲", "orcid": None}]
    assert material["metadata"]["volume"] == "3"
    assert material["metadata"]["pages"] == "1-9"


def test_folder_defaults_to_papers_directory(monkeypatch, tmp_path):
    from researchbase.cli.commands.quick import _papers_folder

    monkeypatch.delenv("RESEARCHBASE_PAPERS_DIR", raising=False)
    assert _papers_folder(None) == Path.home() / "Research" / "papers"
    monkeypatch.setenv("RESEARCHBASE_PAPERS_DIR", str(tmp_path))
    assert _papers_folder(None) == tmp_path
    assert _papers_folder(tmp_path / "other") == tmp_path / "other"


def test_crossref_is_skipped_when_switched_off(monkeypatch):
    from researchbase.cli.commands.quick import _crossref_record

    monkeypatch.setenv("RESEARCHBASE_CROSSREF_LOOKUP", "0")
    assert _crossref_record("10.1234/x", "标题") is None
