"""OpenAlex Works adapter. works-v1 identifies this mapping, not a vendor release."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from researchbase.adapters.literature_http import HttpObservation, get_json
from researchbase.application.literature_search_provider import (
    ProviderError,
    ProviderFailureKind,
    SearchCallContext,
    SearchRequest,
)
from researchbase.domain.literature_search_execution import (
    DeliveryCertainty,
    SearchHit,
    SearchResponse,
)
from researchbase.domain.source_identity import IdentifierType, normalize_source_identifier
from researchbase.foundation.errors import ResearchBaseError


class OpenAlexSearchCapability:
    capability_id = "openalex"
    version = "works-v1"
    supported_source_scopes = frozenset({"BIBLIOGRAPHIC"})
    endpoint = "https://api.openalex.org/works"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        get: Callable[[str, dict[str, str], float], HttpObservation] = get_json,
    ) -> None:
        self._api_key = api_key
        self._get = get

    def search(self, request: SearchRequest, context: SearchCallContext) -> SearchResponse:
        if context.cancellation_requested() or context.remaining_timeout_seconds <= 0:
            raise ProviderError(
                ProviderFailureKind.RETRYABLE,
                "PROVIDER_TRANSIENT",
                delivery_certainty=DeliveryCertainty.NOT_SENT,
            )
        try:
            url = self.request_url(request)
        except (TypeError, ValueError, KeyError) as exc:
            raise ProviderError(ProviderFailureKind.PERMANENT, "PROVIDER_PERMANENT") from exc
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        try:
            observation = self._get(url, headers, min(30.0, context.remaining_timeout_seconds))
        except (ValueError, UnicodeError) as exc:
            raise ProviderError(
                ProviderFailureKind.PERMANENT,
                "PROVIDER_MALFORMED",
                delivery_certainty=DeliveryCertainty.RESPONSE_RECEIVED,
            ) from exc
        except Exception as exc:
            raise ProviderError(ProviderFailureKind.UNCERTAIN, "PROVIDER_OUTCOME_UNKNOWN") from exc
        token = observation.headers.get("x-request-id")
        if token is not None and (not token.strip() or len(token) > 256):
            token = None
        if observation.status != 200:
            retryable = observation.status == 429 or 500 <= observation.status < 600
            retry_after = observation.headers.get("retry-after", "")
            seconds = (
                min(int(retry_after), 2147483647)
                if re.fullmatch(r"[0-9]{1,10}", retry_after)
                else None
            )
            raise ProviderError(
                ProviderFailureKind.RETRYABLE if retryable else ProviderFailureKind.PERMANENT,
                "PROVIDER_RATE_LIMIT"
                if observation.status == 429
                else "PROVIDER_TRANSIENT"
                if retryable
                else "PROVIDER_PERMANENT",
                delivery_certainty=DeliveryCertainty.RESPONSE_RECEIVED,
                provider_request_id=token,
                retry_after_seconds=seconds,
                warning_codes=("RATE_LIMITED",) if observation.status == 429 else (),
            )
        try:
            body = observation.body
            if not isinstance(body, dict) or not isinstance(body.get("results"), list):
                raise ValueError
            count = body["meta"]["count"]
            if (
                isinstance(count, bool)
                or not isinstance(count, int)
                or count < len(body["results"])
            ):
                raise ValueError
            if len(body["results"]) > request.max_results:
                raise ValueError
            hits = tuple(self._hit(work) for work in body["results"])
            return SearchResponse(
                self.capability_id,
                self.version,
                request.query_text,
                token,
                DeliveryCertainty.RESPONSE_RECEIVED,
                hits,
                warning_codes=("RESULTS_TRUNCATED",) if count > len(hits) else (),
                retrieved_at=datetime.now(UTC),
            )
        except (ValueError, TypeError, KeyError, AttributeError, ResearchBaseError) as exc:
            raise ProviderError(
                ProviderFailureKind.PERMANENT,
                "PROVIDER_MALFORMED",
                delivery_certainty=DeliveryCertainty.RESPONSE_RECEIVED,
                provider_request_id=token,
            ) from exc

    def request_url(self, request: SearchRequest) -> str:
        if (
            request.provider_id != self.capability_id
            or request.provider_version != self.version
            or not 1 <= request.max_results <= 100
        ):
            raise ValueError("unsupported request")
        material = request.plan_material
        if not isinstance(material, Mapping) or material.get("source_scope") != "BIBLIOGRAPHIC":
            raise ValueError("unsupported source scope")
        # Inclusion/exclusion statements are human screening rules, never invented API filters.
        params: dict[str, Any] = {
            "search": request.query_text,
            "per_page": request.max_results,
            "page": 1,
            "select": "id,title,doi,relevance_score",
        }
        filters = []
        bounds = material.get("time_range")
        if bounds:
            if bounds.get("from"):
                filters.append("from_publication_date:" + bounds["from"])
            if bounds.get("through"):
                filters.append("to_publication_date:" + bounds["through"])
        languages = material.get("language_scope")
        if languages:
            if any(not re.fullmatch(r"[a-z]{2}", language) for language in languages):
                raise ValueError("unsupported OpenAlex language filter")
            filters.append("language:" + "|".join(languages))
        if filters:
            params["filter"] = ",".join(filters)
        return self.endpoint + "?" + urlencode(params)

    @staticmethod
    def _hit(work: object) -> SearchHit:
        if not isinstance(work, dict):
            raise ValueError
        identifier = normalize_source_identifier(
            IdentifierType.OPENALEX, work["id"]
        ).normalized_value
        doi = work.get("doi")
        url = (
            (
                "https://doi.org/"
                + normalize_source_identifier(IdentifierType.DOI, doi).normalized_value
            )
            if doi
            else "https://openalex.org/" + identifier
        )
        return SearchHit(identifier, work["title"], url, None, work.get("relevance_score"))
