from __future__ import annotations

import pytest

from researchbase.domain.source_identity import (
    IdentifierType,
    normalize_source_identifier,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


@pytest.mark.parametrize(
    ("identifier_type", "value", "normalized", "version_hint"),
    [
        (IdentifierType.DOI, " DOI:10.1234/ABC%7Edef ", "10.1234/abc~def", None),
        (IdentifierType.DOI, "10.1234/Caf%C3%A9", "10.1234/caf%c3%a9", None),
        (IdentifierType.ARXIV, "arXiv:2401.01234v3", "2401.01234", "v3"),
        (IdentifierType.ARXIV, "https://arxiv.org/pdf/2401.01234v2.pdf", "2401.01234", "v2"),
        (IdentifierType.PMID, "000123", "123", None),
        (IdentifierType.ISBN, "0-306-40615-2", "0306406152", None),
        (IdentifierType.SEMANTIC_SCHOLAR, "A" * 40, "a" * 40, None),
        (IdentifierType.OPENALEX, "https://openalex.org/W00042", "W42", None),
        (IdentifierType.URL, "http://192.168.001.001/", "http://192.168.1.1/", None),
        (IdentifierType.URL, "HTTP://Example.COM:80/a/../b#frag", "http://example.com/b", None),
        (
            IdentifierType.URL,
            "https://bücher.example/a//b?Q=%7e#frag",
            "https://xn--bcher-kva.example/a//b?Q=~",
            None,
        ),
        (IdentifierType.URL, "https://example.org/a/%2e%2e/b", "https://example.org/b", None),
        (IdentifierType.OTHER, "local.test:AbC", "local.test:AbC", None),
    ],
)
def test_source_identifier_normalization_vectors(
    identifier_type: IdentifierType,
    value: str,
    normalized: str,
    version_hint: str | None,
) -> None:
    result = normalize_source_identifier(identifier_type, value, namespaces={"local.test"})
    assert result.normalized_value == normalized
    assert result.version_hint == version_hint
    assert result.normalization_version == "source-identifier-normalization-v1"


@pytest.mark.parametrize(
    ("identifier_type", "value"),
    [
        (IdentifierType.DOI, "10.123/abc"),
        (IdentifierType.DOI, "10.1234/a%2Fb"),
        (IdentifierType.DOI, "10.1234/a%FF"),
        (IdentifierType.ARXIV, "2400.1234"),
        (IdentifierType.ARXIV, "https://arxiv.org/pdf/2401.1234?download=1"),
        (IdentifierType.ARXIV, "2401.1234v0"),
        (IdentifierType.PMID, "0"),
        (IdentifierType.ISBN, "0306406153"),
        (IdentifierType.SEMANTIC_SCHOLAR, "g" * 40),
        (IdentifierType.OPENALEX, "W0"),
        (IdentifierType.OPENALEX, "https://openalex.org/w42"),
        (IdentifierType.URL, "https://user:pass@example.org/private"),
        (IdentifierType.URL, "https://example.org/%FF"),
        (IdentifierType.URL, "https://[fe80::1%25eth0]/"),
        (IdentifierType.OTHER, "unknown:value"),
    ],
)
def test_invalid_source_identifiers_have_typed_validation_error(
    identifier_type: IdentifierType, value: str
) -> None:
    with pytest.raises(ResearchBaseError) as error:
        normalize_source_identifier(identifier_type, value)
    assert error.value.code is ErrorCode.IDENTIFIER_INVALID


def test_url_normalization_uses_idna2008_alabels() -> None:
    result = normalize_source_identifier(IdentifierType.URL, "https://bücher.example/")
    assert result.normalized_value == "https://xn--bcher-kva.example/"
