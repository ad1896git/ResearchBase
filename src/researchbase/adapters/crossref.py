"""Narrow Crossref DOI lookup; responses establish bibliographic identity only."""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from researchbase.adapters.literature_http import get_json
from researchbase.domain.source_identity import IdentifierType, normalize_source_identifier
from researchbase.foundation.errors import ResearchBaseError


def title_key(value: str) -> str:
    return " ".join(re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", value).casefold()))


class CrossrefVerifier:
    provider_id = "crossref"
    provider_version = "REST-unversioned"
    adapter_version = "doi-v1"
    endpoint = "https://api.crossref.org/works/"

    def __init__(self, *, get=get_json):
        self._get = get

    def observe(self, doi: str | None, title: str, timeout: int = 15) -> dict[str, Any]:
        started = datetime.now(UTC).isoformat()
        value: dict[str, Any] = {
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "adapter_version": self.adapter_version,
            "endpoint": self.endpoint,
            "request_started_at": started,
            "observed_at": started,
            "outcome": "UNRESOLVED",
            "failure_code": None,
            "http_status": None,
            "metadata": None,
            "evidence": {"assessment": "MISSING_DOI", "original_title": title},
        }
        if doi is None:
            return value
        normalized = normalize_source_identifier(IdentifierType.DOI, doi).normalized_value
        url = self.endpoint + quote(normalized, safe="")
        value["endpoint"] = url
        try:
            response = self._get(url, {}, timeout)
        except Exception as exc:
            value.update(
                outcome="UNAVAILABLE",
                failure_code="TRANSPORT_TIMEOUT"
                if isinstance(exc, TimeoutError)
                else "TRANSPORT_UNKNOWN",
                evidence=None,
                observed_at=datetime.now(UTC).isoformat(),
            )
            return value
        value.update(http_status=response.status, observed_at=datetime.now(UTC).isoformat())
        body = response.body
        message = body.get("message") if isinstance(body, dict) else None
        # Preserve the original permitted bibliographic field values, including conflicts;
        # omit abstract/full text, URLs, credentials, headers and unrelated vendor material.
        permitted = {
            "DOI",
            "title",
            "author",
            "published",
            "published-print",
            "published-online",
            "ISSN",
            "ISBN",
            "container-title",
            "volume",
            "issue",
            "page",
            "type",
        }
        retained = (
            {key: message[key] for key in permitted if key in message}
            if isinstance(message, dict)
            else {}
        )
        if isinstance(retained.get("author"), list):
            retained["author"] = [
                {key: item[key] for key in ("given", "family", "name", "ORCID") if key in item}
                for item in retained["author"]
                if isinstance(item, dict)
            ]
        value["evidence"] = {
            "requested_doi": normalized,
            "original_title": title,
            "response": retained,
            "http_status": response.status,
            "response_sha256": response.payload_sha256,
            "response_truncated": response.payload_truncated,
            "response_failure": response.payload_failure,
            "retention": "bibliographic-fields-v1; abstract and unrelated fields omitted",
            "comparisons": {
                "doi": "NOT_AVAILABLE",
                "title": "NOT_AVAILABLE",
                "authors": "ORIGIN_NOT_AVAILABLE",
                "publication_identifiers": "ORIGIN_NOT_AVAILABLE",
                "publication_date": "ORIGIN_NOT_AVAILABLE",
            },
        }
        if response.status != 200:
            value["outcome"] = "UNRESOLVED" if response.status == 404 else "UNAVAILABLE"
            value["failure_code"] = "HTTP_" + str(response.status)
            return value
        if not isinstance(message, dict):
            value.update(outcome="AMBIGUOUS", failure_code="MALFORMED_RESPONSE")
            return value
        try:
            response_doi = normalize_source_identifier(
                IdentifierType.DOI, message["DOI"]
            ).normalized_value
            titles = message.get("title", [])
            if not isinstance(titles, list) or any(not isinstance(t, str) for t in titles):
                raise ValueError
            authors = []
            for item in retained.get("author", []):
                name = item.get("name") or " ".join(
                    filter(None, [item.get("given"), item.get("family")])
                )
                if name:
                    authors.append({"name": name, "orcid": item.get("ORCID")})
            metadata = {
                "doi": response_doi,
                "type": message.get("type"),
                "title": titles[0] if titles else None,
                "authors": authors,
                "published": retained.get("published"),
                "venue": (message.get("container-title") or [None])[0],
                "journal_identifier": (message.get("ISSN") or message.get("ISBN") or [None])[0],
                "volume": message.get("volume"),
                "issue": message.get("issue"),
                "pages": message.get("page"),
            }
            value["metadata"] = metadata
            comparison = value["evidence"]["comparisons"]
            comparison["doi"] = "MATCH" if normalized == response_doi else "CONFLICT"
            comparison["title"] = (
                "MATCH"
                if titles and title_key(titles[0]) == title_key(title)
                else "CONFLICT"
                if titles
                else "NOT_AVAILABLE"
            )
            value["outcome"] = (
                "CONFLICT"
                if comparison["doi"] == "CONFLICT" or comparison["title"] == "CONFLICT"
                else "MATCH"
                if titles and title_key(title)
                else "AMBIGUOUS"
            )
        except (KeyError, TypeError, ValueError, AttributeError, ResearchBaseError):
            value.update(outcome="AMBIGUOUS", failure_code="MALFORMED_METADATA")
        return value
