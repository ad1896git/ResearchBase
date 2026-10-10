from __future__ import annotations

import pytest


def test_exact_jats_paragraph_and_span():
    from researchbase.adapters.source_document import locate, paragraphs

    content = (
        b"<article><body><sec><p>A result <italic>improved</italic>"
        b" recall.</p></sec></body></article>"
    )
    values = paragraphs(content, "application/jats+xml")
    assert values == ("A result improved recall.",)
    assert locate(values, "improved", paragraph=1, start=9, end=17) == {
        "page": None,
        "section": None,
        "paragraph": "1",
        "figure": None,
        "table": None,
        "quote_span": "char:9:17",
    }


def test_unicode_offsets_relocate_exact_text():
    from researchbase.adapters.source_document import locate, paragraphs, relocate

    values = paragraphs("Café result.\n\nNext paragraph.".encode(), "text/plain")
    locator = locate(values, "Café", paragraph=1, start=0, end=4)
    assert relocate(values, locator) == "Café"


@pytest.mark.parametrize(
    "options",
    [
        {"paragraph": 0, "start": 0, "end": 4},
        {"paragraph": 2, "start": 0, "end": 4},
        {"paragraph": 1, "start": -1, "end": 4},
        {"paragraph": 1, "start": 0, "end": 50},
        {"paragraph": 1, "start": 1, "end": 4},
    ],
)
def test_invalid_or_mismatched_location_rejected(options):
    from researchbase.adapters.source_document import locate
    from researchbase.foundation.errors import ResearchBaseError

    with pytest.raises(ResearchBaseError):
        locate(("text here",), "text", **options)


def test_ambiguous_extraction_requires_explicit_location():
    from researchbase.adapters.source_document import locate
    from researchbase.foundation.errors import ResearchBaseError

    with pytest.raises(ResearchBaseError, match="ambiguous"):
        locate(("same same",), "same")
    assert locate(("same same",), "same", paragraph=1, start=5, end=9)["quote_span"] == "char:5:9"


@pytest.mark.parametrize(
    "content,mime",
    [
        (b"", "text/plain"),
        (b"<article>", "application/jats+xml"),
        (
            b'<!DOCTYPE article [<!ENTITY x "boom">]><article><p>&x;</p></article>',
            "application/jats+xml",
        ),
        (b"fake PDF", "application/pdf"),
        (b"\xff", "text/plain"),
    ],
)
def test_missing_malformed_or_unsupported_document_rejected(content, mime):
    from researchbase.adapters.source_document import paragraphs
    from researchbase.foundation.errors import ResearchBaseError

    with pytest.raises(ResearchBaseError):
        paragraphs(content, mime)


def test_related_is_not_a_support_relation():
    from researchbase.domain.literature_evidence import support_material
    from researchbase.foundation.errors import ResearchBaseError

    with pytest.raises(ResearchBaseError):
        support_material(
            [
                {
                    "literature_evidence": {},
                    "relation_type": "RELATED",
                    "ordinal": 0,
                    "qualification": None,
                }
            ]
        )


def test_r3_evidence_golden_hash():
    from researchbase.domain.literature_evidence import digest, evidence_material

    row = {
        "project_id": "00000000-0000-0000-0000-000000000010",
        "evidence_type": "QUOTATION",
        "locator": {
            "page": "12",
            "section": None,
            "paragraph": None,
            "figure": None,
            "table": None,
            "quote_span": None,
        },
        "extracted_statement": "Café exposure improved recall.",
        "normalized_assertion": None,
        "extraction_method": "HUMAN",
        "confidence": "MODERATE",
    }
    source = {"id": "00000000-0000-0000-0000-000000000001", "content_hash": "d" * 64}
    assert (
        digest(evidence_material(row, source))
        == "6afe3b7c2fb8dc7bfc2f0561055ac18ce2cd8d11a64d5c31783233a03ac57453"
    )
