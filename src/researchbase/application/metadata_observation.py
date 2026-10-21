"""M2 bibliographic observations and minimum result-to-source Application path."""

from __future__ import annotations

import json
import time
from datetime import UTC, date, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4, uuid5

from researchbase.application.source_identity import (
    RegisterLiteratureSource,
    VerifySourceIdentifier,
)
from researchbase.application.source_version import CreateSourceVersion, TransitionSourceVersion
from researchbase.domain.artifact import Artifact, ArtifactId, ArtifactVersion, ArtifactVersionId
from researchbase.domain.organization import ProjectId
from researchbase.domain.source_identity import (
    IdentifierType,
    SourceKind,
    normalize_source_identifier,
    normalize_source_title,
)
from researchbase.domain.source_version import SourceVersionKind, SourceVersionMaterial
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import ContentHash, sha256_canonical_json
from researchbase.foundation.ids import ActorId
from researchbase.foundation.versioning import VersionStatus


class BibliographicMetadataProvider(Protocol):
    provider_id: str
    provider_version: str
    adapter_version: str
    endpoint: str

    def observe(self, doi: str | None, title: str, timeout: int = 15) -> dict[str, Any]: ...


def _hash(row: dict[str, Any]) -> str:
    return str(
        sha256_canonical_json(
            {
                key: value.astimezone(UTC).isoformat()
                if isinstance(value, datetime)
                else str(value)
                if isinstance(value, UUID)
                else value
                for key, value in row.items()
                if key != "content_hash"
            }
        )
    )


class MetadataObservationService:
    def __init__(self, factory, credentials, store, journal, identity, versions):
        self._factory = factory
        self._credentials = credentials
        self._store = store
        self._journal = journal
        self._identity = identity
        self._versions = versions

    def _authorize(self, uow, principal, project, write=True):
        repo = uow.source_version
        repo.lock_project(project)
        facts = repo.authorize(principal, project, None)
        at = repo.at()  # Fresh after authority locks, including credential expiry while waiting.
        if facts is None:
            raise ResearchBaseError(ErrorCode.FORBIDDEN, "current project authority unavailable")
        valid = (
            principal.verified_at <= at
            and self._credentials.is_valid(principal, at)
            and facts["retired_at"] is None
            and facts["membership_status"] == "ACTIVE"
            and facts["binding_status"] == "ACTIVE"
            and facts["bound_at"] <= at
            and (facts["revoked_at"] is None or at < facts["revoked_at"])
            and facts["effective_from"] <= at
            and (facts["effective_until"] is None or at < facts["effective_until"])
            and facts["role"]
            in (
                {"OWNER", "RESEARCHER"}
                if write
                else {"OWNER", "RESEARCHER", "VIEWER", "REVIEWER", "APPROVER"}
            )
            and (not write or uow.literature_search_plan.project_active(project))
        )
        if not valid:
            raise ResearchBaseError(ErrorCode.FORBIDDEN, "current project authority unavailable")
        return at

    def _result(self, uow, result_id, project):
        result = uow.metadata_observations.result(result_id, project)
        if result is None:
            raise ResearchBaseError(ErrorCode.NOT_FOUND, "search result not found")
        uow.literature_search_execution.provenance(result["execution_id"])
        return result

    def observe(
        self, principal, project: UUID, result_id: UUID, invocation_id: UUID, timeout: int = 15
    ):
        if (
            not isinstance(invocation_id, UUID)
            or isinstance(timeout, bool)
            or not 1 <= timeout <= 30
        ):
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "invalid invocation/timeout")
        with self._factory() as uow:
            uow.begin_serializable()
            self._authorize(uow, principal, project)
            result = self._result(uow, result_id, project)
            doi = None
            if result["url"] and result["url"].startswith("https://doi.org/"):
                doi = normalize_source_identifier(
                    IdentifierType.DOI, result["url"]
                ).normalized_value
            fingerprint = str(
                sha256_canonical_json(
                    {
                        "type": "M2_METADATA_REQUEST",
                        "result_id": str(result_id),
                        "result_hash": result["content_hash"],
                        "doi": doi,
                        "provider": self._journal.provider.provider_id,
                        "provider_version": self._journal.provider.provider_version,
                        "adapter": self._journal.provider.adapter_version,
                        "endpoint": self._journal.provider.endpoint,
                        "timeout": timeout,
                    }
                )
            )
            prior = uow.metadata_observations.prior(principal, project, invocation_id)
            if prior:
                self._replay(prior, fingerprint)
                value = self._read(uow, prior)
                uow.commit()
                return value
            uow.commit()
        key = str(
            sha256_canonical_json(
                {
                    "deployment": principal.deployment_id,
                    "project": str(project),
                    "actor": str(principal.actor_id),
                    "invocation": str(invocation_id),
                }
            )
        )
        observation = self._journal.obtain(key, fingerprint, doi, result["title"], timeout)
        evidence = observation["evidence"]
        data = (
            canonical_json_bytes(
                {
                    "type": "BibliographicMetadataObservation",
                    "mapping_version": 1,
                    "metadata": observation["metadata"],
                    "evidence": evidence,
                }
            )
            if evidence is not None
            else None
        )
        identity = self._store.put_verified(data) if data is not None else None
        if identity is not None and not self._store.verify(identity):
            raise ResearchBaseError(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "observation evidence unavailable"
            )
        return self._retry(
            lambda: self._persist(
                principal,
                project,
                result_id,
                invocation_id,
                fingerprint,
                observation,
                data,
                identity,
            )
        )

    def _persist(
        self, principal, project, result_id, invocation_id, fingerprint, observation, data, identity
    ):
        with self._factory() as uow:
            uow.begin_serializable()
            at = self._authorize(uow, principal, project)
            uow.source_version.lock_command(
                principal.deployment_id, project, principal.actor_id, "M2_OBSERVE", invocation_id
            )
            self._result(uow, result_id, project)
            prior = uow.metadata_observations.prior(principal, project, invocation_id)
            if prior:
                self._replay(prior, fingerprint)
                value = self._read(uow, prior)
                uow.commit()
                return value
            artifact_version_id = None
            if data is not None:
                if identity is None or not self._store.verify(identity):
                    raise ResearchBaseError(
                        ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "observation evidence unavailable"
                    )
                artifact_id = ArtifactId(uuid4())
                artifact_version_id = ArtifactVersionId(uuid4())
                uow.artifacts.add(
                    Artifact(
                        artifact_id,
                        ProjectId(project),
                        "metadata_observation",
                        "Bibliographic observation",
                        None,
                        ActorId(principal.actor_id),
                        at,
                    )
                )
                uow.artifact_versions.add(
                    ArtifactVersion(
                        artifact_version_id,
                        artifact_id,
                        1,
                        VersionStatus.FROZEN,
                        identity,
                        "application/json",
                        len(data),
                        ContentHash(identity.removeprefix("sha256:")),
                        None,
                        ActorId(principal.actor_id),
                        at,
                        at,
                    )
                )
                uow.artifacts.update_current_version(artifact_id, artifact_version_id, 1)
            row = {
                "id": uuid4(),
                "project_id": project,
                "result_id": result_id,
                "deployment_id": principal.deployment_id,
                "invocation_id": invocation_id,
                "request_fingerprint": fingerprint,
                "provider_id": observation["provider_id"],
                "provider_version": observation["provider_version"],
                "adapter_version": observation["adapter_version"],
                "endpoint": observation["endpoint"],
                "request_started_at": datetime.fromisoformat(observation["request_started_at"]),
                "observed_at": datetime.fromisoformat(observation["observed_at"]),
                "observed_by": principal.actor_id,
                "outcome": observation["outcome"],
                "failure_code": observation["failure_code"],
                "http_status": observation["http_status"],
                "artifact_version_id": artifact_version_id,
                "source_id": None,
                "source_version_id": None,
                "hash_scheme": "sha256-cjson-v1",
            }
            row["content_hash"] = _hash(row)
            uow.metadata_observations.insert(row)
            value = self._read(uow, row)
            uow.commit()
            return value

    def get(self, principal, project, observation_id) -> dict[str, Any]:
        with self._factory() as uow:
            uow.begin_serializable()
            self._authorize(uow, principal, project, False)
            row = uow.metadata_observations.get(observation_id, project)
            if row is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "observation not found")
            self._result(uow, row["result_id"], project)
            value = self._read(uow, row)
            uow.commit()
            return value

    def list_for_result(self, principal, project, result_id):
        with self._factory() as uow:
            uow.begin_serializable()
            self._authorize(uow, principal, project, False)
            self._result(uow, result_id, project)
            value = {
                "observations": [
                    self._read(uow, row)
                    for row in uow.metadata_observations.list_for_result(result_id)
                ],
                "resolutions": [
                    self._resolution_read(row)
                    for row in uow.metadata_observations.resolutions(result_id)
                ],
            }
            uow.commit()
            return value

    def _read(self, uow, row) -> dict[str, Any]:
        if _hash(row) != row["content_hash"]:
            raise ResearchBaseError(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "observation hash mismatch"
            )
        value = {
            key: item.astimezone(UTC).isoformat()
            if isinstance(item, datetime)
            else str(item)
            if isinstance(item, UUID)
            else item
            for key, item in row.items()
        }
        value["evidence"] = None
        if row["artifact_version_id"] is not None:
            artifact = uow.artifact_versions.get(ArtifactVersionId(row["artifact_version_id"]))
            if (
                artifact is None
                or artifact.status not in {VersionStatus.FROZEN, VersionStatus.SUPERSEDED}
                or not self._store.verify(str(artifact.content_hash))
            ):
                raise ResearchBaseError(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "observation basis unavailable"
                )
            value["evidence"] = json.loads(self._store.open(str(artifact.content_hash)))
        return value

    @staticmethod
    def _resolution_read(row):
        if _hash(row) != row["content_hash"]:
            raise ResearchBaseError(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "resolution hash mismatch"
            )
        return {
            key: item.astimezone(UTC).isoformat()
            if isinstance(item, datetime)
            else str(item)
            if isinstance(item, UUID)
            else item
            for key, item in row.items()
        }

    @staticmethod
    def _replay(prior, fingerprint):
        if prior["request_fingerprint"] != fingerprint:
            raise ResearchBaseError(ErrorCode.IDEMPOTENCY_CONFLICT, "invocation input changed")

    @staticmethod
    def _retry(call):
        for attempt in range(3):
            try:
                return call()
            except ResearchBaseError as exc:
                if exc.code is not ErrorCode.CONCURRENT_MODIFICATION or attempt == 2:
                    raise
                time.sleep(0.01 * (attempt + 1))
        raise AssertionError

    def resolve(self, principal, project, observation_id):
        observation = self.get(principal, project, observation_id)
        if observation["outcome"] != "MATCH":
            return {
                "outcome": observation["outcome"],
                "observation_id": str(observation_id),
                "resolution": None,
            }
        metadata = observation["evidence"]["metadata"]
        title = normalize_source_title(metadata["title"])
        source_kind = {
            "journal-article": SourceKind.PAPER,
            "proceedings-article": SourceKind.PAPER,
            "posted-content": SourceKind.PREPRINT,
            "book": SourceKind.BOOK,
            "monograph": SourceKind.BOOK,
        }.get(metadata.get("type"), SourceKind.OTHER)

        def request(name):
            return uuid5(observation_id, name)

        try:
            source = self._identity.find_source_by_identifier(
                principal, project, IdentifierType.DOI, metadata["doi"]
            )
            if (
                source["title"] != title
                or source["kind"] != source_kind.value
                or source["status"] != "ACTIVE"
            ):
                raise ResearchBaseError(
                    ErrorCode.SOURCE_IDENTITY_CONFLICT, "existing source metadata is incompatible"
                )
        except ResearchBaseError as exc:
            if exc.code is not ErrorCode.SOURCE_NOT_FOUND:
                raise
            source = self._identity.register_literature_source(
                RegisterLiteratureSource(
                    principal,
                    project,
                    source_kind,
                    title,
                    request("source"),
                    IdentifierType.DOI,
                    metadata["doi"],
                )
            )
        source_id = UUID(str(source["source_id"]))
        identifiers = self._identity.list_source_identifiers(principal, project, source_id)
        identifier = next(
            item
            for item in identifiers
            if item["identifier_type"] == "DOI"
            and item["normalized_value"] == metadata["doi"]
            and item["status"] != "REJECTED"
        )
        if identifier["status"] != "VERIFIED":
            self._identity.verify_source_identifier(
                VerifySourceIdentifier(
                    principal,
                    project,
                    UUID(str(identifier["identifier_id"])),
                    UUID(observation["artifact_version_id"]),
                    "Crossref DOI and compatible bibliographic title; "
                    "no scientific claim verification",
                    request("verify"),
                )
            )
        with self._factory() as uow:
            uow.begin_serializable()
            self._authorize(uow, principal, project)
            existing = uow.source_version.source(source_id, project, lock=True)
            current = existing["current_version_id"] if existing else None
            uow.commit()
        if current is None:
            published = None
            try:
                parts = (metadata.get("published") or {}).get("date-parts", [])[0]
                if len(parts) == 3:
                    published = date(*parts)
            except (IndexError, TypeError, ValueError):
                pass
            material = SourceVersionMaterial(
                source_id,
                SourceVersionKind.PREPRINT
                if source_kind is SourceKind.PREPRINT
                else SourceVersionKind.PUBLISHED
                if source_kind in {SourceKind.PAPER, SourceKind.BOOK}
                else SourceVersionKind.OTHER,
                None,
                None,
                title,
                None,
                tuple(metadata["authors"]),
                published,
                metadata.get("venue"),
                None,
                None,
                {
                    key: metadata.get(key)
                    for key in (
                        "journal_identifier",
                        "volume",
                        "issue",
                        "pages",
                        "license_label",
                        "public_repository_label",
                    )
                },
            )
            version = self._versions.create(
                CreateSourceVersion(principal, project, material, request("version"))
            )
            current = UUID(str(version["source_version_id"]))
            self._versions.freeze(
                TransitionSourceVersion(principal, project, current, request("freeze"))
            )
        return self._retry(
            lambda: self._append_resolution(principal, project, observation, source_id, current)
        )

    def _append_resolution(self, principal, project, observation, source_id, version_id):
        result_id = UUID(observation["result_id"])
        with self._factory() as uow:
            uow.begin_serializable()
            at = self._authorize(uow, principal, project)
            self._result(uow, result_id, project)
            row = uow.metadata_observations.resolution(result_id, source_id, version_id)
            if row is None:
                row = {
                    "id": uuid4(),
                    "search_result_record_id": result_id,
                    "source_id": source_id,
                    "source_version_id": version_id,
                    "resolved_by": principal.actor_id,
                    "resolved_at": at,
                    "basis": "Verified DOI and compatible bibliographic title",
                    "hash_scheme": "sha256-cjson-v1",
                }
                row["content_hash"] = _hash(row)
                uow.metadata_observations.insert_resolution(row)
            value = self._resolution_read(row)
            uow.commit()
            return {"outcome": "MATCH", "observation_id": observation["id"], "resolution": value}
