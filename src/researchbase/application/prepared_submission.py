"""B15 Application-only local package preparation, direct consent and history."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, NoReturn, cast
from uuid import UUID, uuid4

from researchbase.application.authorship import AuthorshipService, _ids
from researchbase.application.literature_evidence import LiteratureEvidenceService
from researchbase.application.manuscript_freeze import ManuscriptFreezeService
from researchbase.application.ports import UnitOfWork
from researchbase.application.scientific_conclusion import ScientificConclusionService
from researchbase.domain.authorship import ExactReference
from researchbase.domain.literature_evidence import TRANSITIONS, digest, evidence_material
from researchbase.domain.manuscript import ManuscriptReference
from researchbase.domain.phase2_identity import CredentialVerifier, VerifiedPrincipal
from researchbase.domain.prepared_submission import (
    ConsentScope,
    ConsentState,
    ManifestItemReadback,
    PackageStatus,
    Validity,
    ValidityReason,
    consent_chain,
    consent_material,
    manifest_material,
    project_occurrences,
    withdrawal_reason,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_bytes, sha256_canonical_json

_READERS = frozenset({"OWNER", "RESEARCHER", "VIEWER", "REVIEWER", "APPROVER"})
_WRITERS = frozenset({"OWNER", "RESEARCHER"})
_TARGETS: dict[str, tuple[str, str, Any]] = {
    "FIGURE": ("artifact_version_id", "artifact_versions", "ArtifactVersion"),
    "TABLE": ("artifact_version_id", "artifact_versions", "ArtifactVersion"),
    "CITATION": ("source_version_id", "source_versions", "SourceVersion"),
    "CLAIM": ("claim_version_id", "claim_versions", "ClaimVersion"),
    "CONCLUSION": (
        "scientific_conclusion_version_id",
        "scientific_conclusion_versions",
        "ScientificConclusionVersion",
    ),
}


def _fail(code, message) -> NoReturn:
    raise ResearchBaseError(code, message)


def _validate_ids(*identities):
    try:
        _ids(*identities)
    except (TypeError, ValueError):
        _fail(ErrorCode.VALIDATION_ERROR, "exact UUID fields required")


@dataclass(frozen=True, slots=True)
class PrepareSubmissionCommand:
    id: UUID
    project_id: UUID
    publication_id: UUID
    manuscript_version_id: UUID
    authorship_snapshot_id: UUID

    def __post_init__(self):
        _validate_ids(
            self.id,
            self.project_id,
            self.publication_id,
            self.manuscript_version_id,
            self.authorship_snapshot_id,
        )


@dataclass(frozen=True, slots=True)
class RecordAuthorConsentCommand:
    id: UUID
    project_id: UUID
    prepared_submission_version_id: UUID
    consent_state: ConsentState
    consent_scope: ConsentScope
    evidence_artifact_version_id: UUID
    prior_consent_id: UUID | None

    def __post_init__(self):
        _validate_ids(
            self.id,
            self.project_id,
            self.prepared_submission_version_id,
            self.evidence_artifact_version_id,
        )
        if (
            type(self.consent_state) is not str
            or self.consent_state not in {"GRANTED", "WITHDRAWN"}
            or type(self.consent_scope) is not str
            or self.consent_scope != "PREPARED_PACKAGE"
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "closed consent state and scope required")
        if self.consent_state == "WITHDRAWN" and self.prior_consent_id is None:
            _fail(ErrorCode.INVALID_STATE_TRANSITION, "withdrawal requires prior GRANTED head")
        if self.prior_consent_id is not None:
            _validate_ids(self.prior_consent_id)


@dataclass(frozen=True, slots=True)
class WithdrawPreparedSubmissionCommand:
    project_id: UUID
    prepared_submission_version_id: UUID
    reason: str

    def __post_init__(self):
        _validate_ids(self.project_id, self.prepared_submission_version_id)
        try:
            object.__setattr__(self, "reason", withdrawal_reason(self.reason))
        except (ValueError, TypeError):
            _fail(ErrorCode.VALIDATION_ERROR, "nonblank Unicode withdrawal reason required")


@dataclass(frozen=True, slots=True)
class GetPreparedSubmissionQuery:
    project_id: UUID
    prepared_submission_version_id: UUID

    def __post_init__(self):
        _validate_ids(self.project_id, self.prepared_submission_version_id)


@dataclass(frozen=True, slots=True)
class GetAuthorConsentQuery:
    project_id: UUID
    id: UUID

    def __post_init__(self):
        _validate_ids(self.project_id, self.id)


@dataclass(frozen=True, slots=True)
class GetOwnAuthorConsentQuery:
    project_id: UUID
    prepared_submission_version_id: UUID
    id: UUID

    def __post_init__(self):
        _validate_ids(self.project_id, self.prepared_submission_version_id, self.id)


@dataclass(frozen=True, slots=True)
class AuthorConsentReadback:
    id: UUID
    project_id: UUID
    prepared_submission_version_id: UUID
    actor_id: UUID
    consent_state: ConsentState
    consent_scope: ConsentScope
    evidence_artifact: ExactReference
    prior_consent: ExactReference | None
    captured_at: datetime
    content_hash: str
    hash_scheme: Literal["sha256-cjson-v1"]


@dataclass(frozen=True, slots=True)
class OwnAuthorConsentReadback:
    consent: AuthorConsentReadback
    current_head: AuthorConsentReadback


@dataclass(frozen=True, slots=True)
class PreparedSubmissionEventReadback:
    id: UUID
    prepared_submission_version_id: UUID
    prior_status: Literal["PREPARED"] | None
    new_status: PackageStatus
    actor_id: UUID
    occurred_at: datetime
    reason: str | None


@dataclass(frozen=True, slots=True)
class PreparedSubmissionReadback:
    id: UUID
    project_id: UUID
    publication_id: UUID
    version_number: int
    manuscript_version_id: UUID
    authorship_snapshot_id: UUID
    status: PackageStatus
    row_version: int
    package_manifest_hash: None
    content_hash: None
    hash_scheme: Literal["sha256-cjson-v1"]
    frozen_at: None
    created_by: UUID
    created_at: datetime
    items: tuple[ManifestItemReadback, ...]
    consents: tuple[AuthorConsentReadback, ...]
    events: tuple[PreparedSubmissionEventReadback, ...]
    grant_id: None
    consumption_id: None
    current_validity: Validity
    validity_reasons: tuple[ValidityReason, ...]


@dataclass(frozen=True, slots=True)
class PreparedSubmissionHistory:
    prepared_submission_version_id: UUID
    publication_id: UUID
    manuscript_version_id: UUID
    authorship_snapshot_id: UUID
    events: tuple[PreparedSubmissionEventReadback, ...]


@dataclass(frozen=True, slots=True)
class PreparedSubmissionPreview:
    prepared_submission_version_id: UUID
    items: tuple[ManifestItemReadback, ...]
    candidate_manifest_hash: str | None
    missing_author_ids: tuple[UUID, ...]
    current_validity: Validity
    validity_reasons: tuple[ValidityReason, ...]


class _RetainedLiteratureVerifier(LiteratureEvidenceService):
    """Retain hash/history inspection when exact document passage bytes are absent."""

    def __init__(self, factory, credentials, store, unavailable):
        super().__init__(factory, credentials, store)
        self.unavailable = unavailable

    def _artifact(self, uow, identity, project):
        row = uow.literature_evidence.artifact(identity, project)
        if row and row["status"] in {"FROZEN", "SUPERSEDED"}:
            try:
                if self._store is None:
                    raise FileNotFoundError()
                self._store.open(row["locator"])
            except OSError:
                metadata = row["metadata"]
                if (
                    row["locator"] != "sha256:" + row["content_hash"]
                    or row["frozen_at"] is None
                    or row["byte_size"] is None
                    or not isinstance(metadata, dict)
                    or metadata.get("access") != "PROJECT_LOCAL"
                    or metadata.get("parser") != "manual-document-v1"
                    or not metadata.get("retention_basis")
                ):
                    _fail(
                        ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid retained source metadata"
                    )
                ExactReference("ArtifactVersion", identity, row["content_hash"])
                self.unavailable.add(identity)
                return {
                    "artifact_id": row["artifact_id"],
                    "artifact_version_id": identity,
                    "content_hash": row["content_hash"],
                    "media_type": row["media_type"],
                    "byte_size": row["byte_size"],
                    "retention_basis": metadata["retention_basis"],
                    "access": "PROJECT_LOCAL",
                    "parser": "manual-document-v1",
                }, None
        return super()._artifact(uow, identity, project)

    def _read_saved(self, uow, row, project):
        source, artifact, values, valid = self._source(uow, row["source_version_id"], project)
        if values is not None:
            return super()._read_saved(uow, row, project)
        if digest(evidence_material(row, source)) != row["content_hash"]:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "retained evidence hash mismatch")
        events = uow.literature_evidence.events(row["id"])
        status = "UNREVIEWED"
        for event in events:
            if event["prior_status"] != status or event["new_status"] not in TRANSITIONS[status]:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "retained review history mismatch")
            status = event["new_status"]
        if row["review_status"] != status:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "retained review state mismatch")
        return {
            **artifact,
            **row,
            "document_content_hash": artifact["content_hash"],
            "source_version_hash": source["content_hash"],
            "source_validity": valid,
            "review_events": events,
        }


class _RetainedVerifier(ManuscriptFreezeService):
    """Missing bytes are diagnostics in history, never successful admission."""

    def __init__(self, factory, credentials, store, unavailable):
        super().__init__(factory, credentials, store)
        self.unavailable = unavailable
        self._literature = _RetainedLiteratureVerifier(factory, credentials, store, unavailable)
        self._conclusions = ScientificConclusionService(factory, credentials, self._literature)

    def _artifact(self, uow, project, identity, *, document=False, admission=False):
        row = uow.manuscript_freeze.artifact(identity, project)
        if row and row["status"] in {"FROZEN", "SUPERSEDED"} and row["frozen_at"] is not None:
            try:
                if self._store is None:
                    raise FileNotFoundError()
                self._store.open(row["content_hash"])
            except OSError:
                if (document and row["artifact_type"] != "manuscript") or row["byte_size"] is None:
                    _fail(
                        ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid retained artifact metadata"
                    )
                self.unavailable.add(identity)
                return ManuscriptReference(
                    "ArtifactVersion", identity, row["content_hash"]
                ), self._validity(uow, project, "artifact_version", identity)
        return super()._artifact(uow, project, identity, document=document, admission=admission)


class PreparedSubmissionService:
    def __init__(
        self, factory: Callable[[], UnitOfWork], credentials: CredentialVerifier, store: Any
    ):
        self._factory, self._credentials, self._store = factory, credentials, store
        self._authorship = AuthorshipService(factory, credentials)

    def _boundary(self, principal, value, expected):
        self._authorship._boundary(principal, value, expected)

    def _authorize(self, uow, principal, project, roles=_READERS):
        return self._authorship._authorize(uow.authorship, principal, project, roles).astimezone(
            UTC
        )

    def _stage(self, uow, principal, project, publication, roles):
        at = self._authorize(uow, principal, project, roles)
        parent = uow.prepared_submission.parent(publication)
        if parent is None or parent["project_id"] != project:
            _fail(ErrorCode.FORBIDDEN, "publication outside requested project")
        if parent["lifecycle_status"] not in {"DRAFTING", "INTERNAL_REVIEW", "READY"}:
            _fail(ErrorCode.INVALID_STATE_TRANSITION, "publication stage disallows preparation")
        # Consent authors may have only VIEWER; active project is still mandatory.
        if not any(
            r["lifecycle_status"] == "ACTIVE" for r in uow.authorship.authority(principal, project)
        ):
            _fail(ErrorCode.INVALID_STATE_TRANSITION, "active project required")
        return at

    def _package(self, uow, identity, project):
        row = uow.prepared_submission.package(identity)
        if row is None:
            _fail(ErrorCode.NOT_FOUND, "exact package unavailable")
        parent = uow.prepared_submission.parent(row["publication_id"])
        if parent is None or parent["project_id"] != project:
            _fail(ErrorCode.FORBIDDEN, "package outside requested project")
        return row, parent

    def _snapshot(self, uow, row, project, *, admission=False):
        snapshot = uow.authorship.snapshot(row["authorship_snapshot_id"])
        if snapshot is None:
            _fail(
                ErrorCode.NOT_FOUND if admission else ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "exact snapshot unavailable",
            )
        self._authorship._scoped(uow.authorship, snapshot, project)
        if snapshot["publication_id"] != row["publication_id"]:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "same-publication snapshot required")
        return self._authorship._snapshot(uow.authorship, snapshot, project)

    def _projection(self, uow, manuscript, authors):
        placements = []
        for kind, rows in (
            ("artifact", uow.publication.artifact_placements(manuscript)),
            ("citation", uow.publication.citations(manuscript)),
            ("claim", uow.publication.claim_placements(manuscript)),
        ):
            for item in rows:
                category = (
                    item["artifact_role"]
                    if kind == "artifact"
                    else "CITATION"
                    if kind == "citation"
                    else "CLAIM"
                    if item["claim_version_id"] is not None
                    else "CONCLUSION"
                )
                if category not in _TARGETS:
                    _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "unsupported direct placement")
                column, table, target_type = _TARGETS[category]
                target = uow.prepared_submission.target(table, item[column])
                if target is None:
                    _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "missing exact target")
                placements.append(
                    (
                        category,
                        item["section_id"],
                        item["ordinal"],
                        ExactReference(target_type, target["id"], target["content_hash"]),
                    )
                )
        try:
            return project_occurrences(placements, len(authors))
        except (ValueError, TypeError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid occurrence aggregate")

    def _events(self, uow, row):
        events = uow.prepared_submission.events(row["id"])
        expected = 1 if row["status"] == "PREPARED" else 2 if row["status"] == "WITHDRAWN" else 0
        if (
            len(events) != expected
            or row["row_version"] != expected
            or expected == 0
            or row["package_manifest_hash"] is not None
            or row["content_hash"] is not None
            or row["frozen_at"] is not None
            or row["hash_scheme"] != "sha256-cjson-v1"
            or not 1 <= row["version_number"] <= 2147483647
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid package history")
        for index, event in enumerate(events):
            if (
                event["actor_id"] != event["created_by"]
                or event["occurred_at"] != event["created_at"]
                or event["prior_status"] != (None if index == 0 else "PREPARED")
                or event["new_status"] != ("PREPARED" if index == 0 else "WITHDRAWN")
                or (
                    index == 0
                    and (
                        event["reason"] is not None
                        or event["actor_id"] != row["created_by"]
                        or event["occurred_at"] != row["created_at"]
                    )
                )
            ):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "contradictory package event")
            if index:
                try:
                    if (
                        withdrawal_reason(event["reason"]) != event["reason"]
                        or event["occurred_at"] < row["created_at"]
                    ):
                        raise ValueError()
                except (ValueError, TypeError):
                    _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid withdrawal event")
        return tuple(
            PreparedSubmissionEventReadback(
                e["id"],
                row["id"],
                e["prior_status"],
                e["new_status"],
                e["actor_id"],
                e["occurred_at"].astimezone(UTC),
                e["reason"],
            )
            for e in events
        )

    def _structure(self, uow, row, project):
        uow.enable_revision_action_snapshot_reads()
        snapshot = self._snapshot(uow, row, project)
        projection = self._projection(uow, row["manuscript_version_id"], snapshot.authors)
        items = []
        for item in uow.prepared_submission.items(row["id"]):
            if item["category"] not in _TARGETS:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "non-consent items required")
            column, table, target_type = _TARGETS[item["category"]]
            target = uow.prepared_submission.target(table, item[column])
            try:
                if (
                    item["created_by"] != row["created_by"]
                    or item["created_at"] != row["created_at"]
                ):
                    raise ValueError()
                items.append(
                    ManifestItemReadback(
                        item["id"],
                        item["category"],
                        item["ordinal"],
                        ExactReference(target_type, target["id"], target["content_hash"]),
                    )
                )
            except (TypeError, ValueError, KeyError):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid stored occurrence")
        if tuple((i.category, i.ordinal, i.target) for i in items) != projection:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "occurrence mismatch")
        return snapshot, tuple(items), self._events(uow, row)

    def _context(self, uow, row, parent, project, *, admission=False):
        manuscript = uow.prepared_submission.manuscript(row["manuscript_version_id"])
        if manuscript is None:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "exact manuscript unavailable")
        owner = uow.prepared_submission.parent(manuscript["publication_id"])
        if owner is None or owner["project_id"] != project:
            _fail(ErrorCode.FORBIDDEN, "manuscript outside requested project")
        if manuscript["publication_id"] != row["publication_id"]:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "same-parent manuscript required")
        if manuscript["status"] != "FROZEN":
            _fail(ErrorCode.VERSION_NOT_FROZEN, "exact FROZEN manuscript required")
        unavailable = set()
        verifier = _RetainedVerifier(self._factory, self._credentials, self._store, unavailable)
        verified = verifier.verify_in_uow(uow, project, parent, manuscript, require_current=False)
        if admission and unavailable:
            _fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "retained bytes required")
        if admission and verified.current_validity != "VALID":
            _fail(ErrorCode.INVALID_STATE_TRANSITION, "current upstream validity required")
        return verified, unavailable

    def _evidence(self, uow, identity, project, *, allow_missing=False):
        row = uow.manuscript_freeze.artifact(identity, project)
        if row is None:
            _fail(ErrorCode.FORBIDDEN, "accessible same-project evidence required")
        if row["status"] not in {"FROZEN", "SUPERSEDED"} or row["frozen_at"] is None:
            _fail(ErrorCode.VERSION_NOT_FROZEN, "frozen consent evidence required")
        try:
            ref = ExactReference("ArtifactVersion", identity, row["content_hash"])
            if self._store is None:
                raise FileNotFoundError()
            data = self._store.open(ref.content_hash)
        except (FileNotFoundError, OSError):
            if allow_missing:
                return ExactReference("ArtifactVersion", identity, row["content_hash"]), True
            _fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "retained evidence bytes required")
        except (ValueError, TypeError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid evidence reference")
        if (
            len(data) != row["byte_size"]
            or str(sha256_bytes(data)) != ref.content_hash
            or not self._store.verify(ref.content_hash)
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "evidence bytes/hash contradiction")
        return ref, False

    def _chain(self, uow, package, actor, project):
        snapshot = self._snapshot(uow, package, project)
        if actor not in {a.actor_id for a in snapshot.authors}:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "consent author outside snapshot")
        try:
            rows = consent_chain(
                [
                    r
                    for r in uow.prepared_submission.consents(package["id"])
                    if r["actor_id"] == actor
                ]
            )
            heads = uow.prepared_submission.heads(package["id"], actor)
            if tuple(h["id"] for h in heads) != ((rows[-1]["id"],) if rows else ()):
                raise ValueError("unique anti-successor head required")
            result = []
            for row in rows:
                evidence = uow.manuscript_freeze.artifact(
                    row["evidence_artifact_version_id"], project
                )
                if (
                    evidence is None
                    or evidence["status"] not in {"FROZEN", "SUPERSEDED"}
                    or evidence["frozen_at"] is None
                ):
                    raise ValueError("retained frozen evidence required")
                ref = ExactReference("ArtifactVersion", evidence["id"], evidence["content_hash"])
                prior = (
                    ExactReference("AuthorConsent", result[-1].id, result[-1].content_hash)
                    if result
                    else None
                )
                expected = str(
                    sha256_canonical_json(
                        consent_material(package["id"], actor, ref, row["consent_state"], prior)
                    )
                )
                if (
                    row["actor_id"] != row["created_by"]
                    or row["consent_scope"] != "PREPARED_PACKAGE"
                    or row["captured_at"] != row["created_at"]
                    or row["content_hash"] != expected
                    or row["hash_scheme"] != "sha256-cjson-v1"
                ):
                    raise ValueError("consent hash or metadata mismatch")
                result.append(
                    AuthorConsentReadback(
                        row["id"],
                        project,
                        package["id"],
                        actor,
                        row["consent_state"],
                        "PREPARED_PACKAGE",
                        ref,
                        prior,
                        row["captured_at"].astimezone(UTC),
                        expected,
                        "sha256-cjson-v1",
                    )
                )
            return tuple(result)
        except (ValueError, TypeError, KeyError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid consent chain")

    def _consent(self, uow, row, project, *, allow_missing=False, metadata_only=False):
        package, _ = self._package(uow, row["prepared_submission_version_id"], project)
        chain = self._chain(uow, package, row["actor_id"], project)
        for consent in chain:
            if consent.id == row["id"]:
                if metadata_only:
                    return consent, False
                _, unavailable = self._evidence(
                    uow, consent.evidence_artifact.id, project, allow_missing=allow_missing
                )
                return consent, unavailable
        _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "disconnected consent")

    def _self_authorize(self, uow, principal):
        at = uow.authorship.at()
        if type(principal) is not VerifiedPrincipal:
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        binding = uow.phase2_identity.resolve_bound_subject(principal)
        try:
            live = principal.verified_at <= at and self._credentials.is_valid(principal, at)
        except Exception:
            live = False
        if (
            not live
            or binding is None
            or binding["actor_id"] != principal.actor_id
            or binding["retired_at"] is not None
            or binding["bound_at"] > at
            or (binding["revoked_at"] is not None and at >= binding["revoked_at"])
            or getattr(principal, "acting_on_behalf_of", None) is not None
        ):
            _fail(ErrorCode.FORBIDDEN, "own consent unavailable")
        return at.astimezone(UTC)

    def _own_route(self, uow, principal, project, package_id, consent_id):
        self._self_authorize(uow, principal)
        consent = uow.prepared_submission.consent(consent_id)
        package = uow.prepared_submission.package(package_id)
        parent = uow.prepared_submission.parent(package["publication_id"]) if package else None
        if (
            consent is None
            or package is None
            or parent is None
            or parent["project_id"] != project
            or consent["actor_id"] != principal.actor_id
            or consent["prepared_submission_version_id"] != package_id
        ):
            _fail(ErrorCode.FORBIDDEN, "own consent unavailable")
        return package, parent

    def get_own_author_consent(
        self, principal, query: GetOwnAuthorConsentQuery
    ) -> OwnAuthorConsentReadback:
        if type(principal) is not VerifiedPrincipal:
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(query) is not GetOwnAuthorConsentQuery:
            _fail(ErrorCode.VALIDATION_ERROR, "closed query required")
        with self._factory() as uow:
            uow.enable_package_preparation_error_normalization()
            uow.begin_formal_read()
            package, _ = self._own_route(
                uow, principal, query.project_id, query.prepared_submission_version_id, query.id
            )
            chain = self._chain(uow, package, principal.actor_id, query.project_id)
            saved = next(c for c in chain if c.id == query.id)
            self._self_authorize(uow, principal)
            return OwnAuthorConsentReadback(saved, chain[-1])

    def _readback(self, uow, row, parent, project):
        snapshot, items, events = self._structure(uow, row, project)
        verified, unavailable = self._context(uow, row, parent, project)
        roots = []
        heads = []
        for author in snapshot.authors:
            chain = self._chain(uow, row, author.actor_id, project)
            roots.extend(chain)
            for consent in chain[-1:]:
                _, absent = self._evidence(
                    uow, consent.evidence_artifact.id, project, allow_missing=True
                )
                if absent:
                    unavailable.add(consent.evidence_artifact.id)
            if chain and chain[-1].consent_state == "GRANTED":
                heads.append(chain[-1])
        authors = tuple(a.actor_id for a in snapshot.authors)
        missing = tuple(a for a in authors if a not in {c.actor_id for c in heads})
        reasons = {"NOT_FROZEN"}
        if missing:
            reasons.add("CONSENT_MISSING")
        validity = "NOT_FROZEN"
        if verified.current_validity in {"STALE", "INVALID"}:
            validity = verified.current_validity
            reasons.add("UPSTREAM_" + validity)
        if row["status"] == "WITHDRAWN":
            reasons.add("PACKAGE_WITHDRAWN")
            if validity != "INVALID":
                validity = "STALE"
        if unavailable:
            reasons.add("DEPENDENCY_UNAVAILABLE")
        result = PreparedSubmissionReadback(
            row["id"],
            project,
            row["publication_id"],
            row["version_number"],
            row["manuscript_version_id"],
            row["authorship_snapshot_id"],
            row["status"],
            row["row_version"],
            None,
            None,
            "sha256-cjson-v1",
            None,
            row["created_by"],
            row["created_at"].astimezone(UTC),
            items,
            tuple(roots),
            events,
            None,
            None,
            cast(Validity, validity),
            cast(tuple[ValidityReason, ...], tuple(sorted(reasons))),
        )
        return result, snapshot, verified, missing

    def _read(self, principal, query, mode) -> Any:
        with self._factory() as uow:
            uow.enable_package_preparation_error_normalization()
            uow.begin_formal_read()
            self._authorize(uow, principal, query.project_id)
            if mode == "consent":
                row = uow.prepared_submission.consent(query.id)
                if row is None:
                    _fail(ErrorCode.NOT_FOUND, "exact consent unavailable")
                result, _ = self._consent(uow, row, query.project_id)
            else:
                row, parent = self._package(
                    uow, query.prepared_submission_version_id, query.project_id
                )
                result, snapshot, manuscript, missing = self._readback(
                    uow, row, parent, query.project_id
                )
                if mode == "history":
                    result = PreparedSubmissionHistory(
                        row["id"],
                        row["publication_id"],
                        row["manuscript_version_id"],
                        row["authorship_snapshot_id"],
                        result.events,
                    )
                elif mode == "preview":
                    items = result.items + tuple(
                        ManifestItemReadback(
                            c.id,
                            "AUTHOR_CONSENT",
                            index,
                            ExactReference("AuthorConsent", c.id, c.content_hash),
                        )
                        for index, author in enumerate(snapshot.authors)
                        for c in result.consents
                        if c.actor_id == author.actor_id
                        and c.consent_state == "GRANTED"
                        and not any(
                            x.prior_consent and x.prior_consent.id == c.id for x in result.consents
                        )
                    )
                    # Missing authors retain their reserved authored ordinal.
                    candidate = None
                    if result.validity_reasons == ("NOT_FROZEN",):
                        candidate = str(
                            sha256_canonical_json(
                                manifest_material(
                                    ExactReference(
                                        "ManuscriptVersion",
                                        row["manuscript_version_id"],
                                        cast(str, manuscript.content_hash),
                                    ),
                                    ExactReference(
                                        "AuthorshipSnapshot", snapshot.id, snapshot.content_hash
                                    ),
                                    items,
                                )
                            )
                        )
                    result = PreparedSubmissionPreview(
                        row["id"],
                        tuple(sorted(items, key=lambda i: (i.category, i.ordinal))),
                        candidate,
                        missing,
                        result.current_validity,
                        result.validity_reasons,
                    )
            self._authorize(uow, principal, query.project_id)
            return result

    def get_prepared_submission(
        self, principal: VerifiedPrincipal, query: GetPreparedSubmissionQuery
    ) -> PreparedSubmissionReadback:
        self._boundary(principal, query, GetPreparedSubmissionQuery)
        return self._read(principal, query, "package")

    def get_prepared_submission_history(
        self, principal: VerifiedPrincipal, query: GetPreparedSubmissionQuery
    ) -> PreparedSubmissionHistory:
        self._boundary(principal, query, GetPreparedSubmissionQuery)
        return self._read(principal, query, "history")

    def preview_prepared_submission(
        self, principal: VerifiedPrincipal, query: GetPreparedSubmissionQuery
    ) -> PreparedSubmissionPreview:
        self._boundary(principal, query, GetPreparedSubmissionQuery)
        return self._read(principal, query, "preview")

    def get_author_consent(
        self, principal: VerifiedPrincipal, query: GetAuthorConsentQuery
    ) -> AuthorConsentReadback:
        self._boundary(principal, query, GetAuthorConsentQuery)
        return self._read(principal, query, "consent")

    def _compare(self, uow, principal, command, mode):
        repo = uow.prepared_submission
        project = command.project_id
        self._authorize(uow, principal, project)
        if mode == "prepare":
            row = repo.package(command.id)
            if row is None:
                return None
            row, parent = self._package(uow, row["id"], project)
            if (
                row["created_by"],
                row["publication_id"],
                row["manuscript_version_id"],
                row["authorship_snapshot_id"],
            ) != (
                principal.actor_id,
                command.publication_id,
                command.manuscript_version_id,
                command.authorship_snapshot_id,
            ):
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "package UUID material differs")
            return self._readback(uow, row, parent, project)[0]
        row, _ = self._package(uow, command.prepared_submission_version_id, project)
        events = self._events(uow, row)
        if row["status"] == "PREPARED":
            return None
        event = events[-1]
        if event.actor_id != principal.actor_id or event.reason != command.reason:
            _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "withdrawal material differs")
        return event

    def _execute(self, principal, command, mode) -> Any:
        # Completed replay is always a lock-free read snapshot.
        with self._factory() as uow:
            uow.enable_package_preparation_error_normalization()
            uow.begin_formal_read()
            replay = self._compare(uow, principal, command, mode)
            self._authorize(uow, principal, command.project_id)
            if replay is not None:
                return replay
        for attempt in range(3):
            try:
                return self._write(principal, command, mode)
            except ResearchBaseError as error:
                if (error.details or {}).get("retryable_b15") and attempt < 2:
                    continue
                raise ResearchBaseError(error.code, error.message) from None
        raise AssertionError("unreachable retry")

    def prepare_submission(
        self, principal: VerifiedPrincipal, command: PrepareSubmissionCommand
    ) -> PreparedSubmissionReadback:
        self._boundary(principal, command, PrepareSubmissionCommand)
        return self._execute(principal, command, "prepare")

    def record_author_consent(
        self, principal: VerifiedPrincipal, command: RecordAuthorConsentCommand
    ) -> AuthorConsentReadback:
        if type(principal) is not VerifiedPrincipal:
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(command) is not RecordAuthorConsentCommand:
            _fail(ErrorCode.VALIDATION_ERROR, "closed consent command required")
        for attempt in range(3):
            try:
                replay = self._consent_replay(principal, command)
                if replay is not None:
                    return replay
                result = self._write_consent(principal, command)
                if result is not None:
                    return result
                replay = self._consent_replay(principal, command)
                if replay is None:
                    _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "committed replay unavailable")
                return replay
            except ResearchBaseError as error:
                if (error.details or {}).get("consent_unique_b16"):
                    replay = self._consent_replay(principal, command)
                    if replay is not None:
                        return replay
                if (error.details or {}).get("retryable_b15") and attempt < 2:
                    continue
                raise ResearchBaseError(error.code, error.message) from None
        raise AssertionError("unreachable")

    def withdraw_prepared_submission(
        self, principal: VerifiedPrincipal, command: WithdrawPreparedSubmissionCommand
    ) -> PreparedSubmissionEventReadback:
        self._boundary(principal, command, WithdrawPreparedSubmissionCommand)
        return self._execute(principal, command, "withdraw")

    def _consent_permission(self, uow, principal, command):
        if command.consent_state == "WITHDRAWN":
            return self._own_route(
                uow,
                principal,
                command.project_id,
                command.prepared_submission_version_id,
                command.prior_consent_id,
            )
        self._authorize(uow, principal, command.project_id)
        return self._package(uow, command.prepared_submission_version_id, command.project_id)

    def _consent_replay(self, principal, command):
        with self._factory() as uow:
            uow.enable_package_preparation_error_normalization()
            uow.begin_formal_read()
            package, _ = self._consent_permission(uow, principal, command)
            row = uow.prepared_submission.consent(command.id)
            if row is None:
                return None
            if (
                row["actor_id"],
                row["prepared_submission_version_id"],
                row["consent_state"],
                row["consent_scope"],
                row["evidence_artifact_version_id"],
                row["prior_consent_id"],
            ) != (
                principal.actor_id,
                package["id"],
                command.consent_state,
                command.consent_scope,
                command.evidence_artifact_version_id,
                command.prior_consent_id,
            ):
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "consent UUID material differs")
            result = self._consent(uow, row, command.project_id, metadata_only=True)[0]
            self._consent_permission(uow, principal, command)
            return result

    def _write_consent(self, principal, command):
        with self._factory() as uow:
            uow.enable_package_preparation_error_normalization()
            repo = uow.prepared_submission
            repo.prepare_consent_write()
            uow.enable_revision_action_snapshot_reads()
            repo.coordinate(f"b15:consent:{command.id}")
            package, parent = self._consent_permission(uow, principal, command)
            uow.approval.lock_scope(command.project_id, "PREPARE_SUBMISSION")
            repo.manuscript(package["manuscript_version_id"], lock=True)
            repo.parent(parent["id"], lock=True)
            package = repo.package(package["id"], lock=True)
            if package is None:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "protected package unavailable")
            repo.lock_chain(package["id"], principal.actor_id)
            self._consent_permission(uow, principal, command)
            if repo.consent(command.id) is not None:
                return None
            self._self_authorize(uow, principal)
            snapshot = self._snapshot(uow, package, command.project_id)
            if principal.actor_id not in {a.actor_id for a in snapshot.authors}:
                _fail(ErrorCode.FORBIDDEN, "direct HUMAN snapshot author required")
            chain = self._chain(uow, package, principal.actor_id, command.project_id)
            head = chain[-1] if chain else None
            if (head.id if head else None) != command.prior_consent_id:
                _fail(ErrorCode.CONCURRENT_MODIFICATION, "current consent head required")
            if head and head.consent_state == command.consent_state:
                _fail(ErrorCode.INVALID_STATE_TRANSITION, "alternating consent required")
            withdrawing = command.consent_state == "WITHDRAWN"
            retained = next(
                (
                    c.evidence_artifact
                    for c in chain
                    if c.evidence_artifact.id == command.evidence_artifact_version_id
                ),
                None,
            )
            if withdrawing and retained is not None:
                evidence = retained
            else:
                if withdrawing:
                    self._authorize(uow, principal, command.project_id)
                else:
                    self._stage(uow, principal, command.project_id, parent["id"], _READERS)
                evidence, _ = self._evidence(
                    uow, command.evidence_artifact_version_id, command.project_id
                )
            if not withdrawing:
                if package["status"] != "PREPARED":
                    _fail(ErrorCode.INVALID_STATE_TRANSITION, "package withdrawn")
                self._structure(uow, package, command.project_id)
                self._context(uow, package, parent, command.project_id, admission=True)
            grants = ()
            if withdrawing:
                if repo.related_grants(package["id"], command.project_id, contradiction=True):
                    _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "ACTIVE grant has receipt")
                grants = repo.related_grants(package["id"], command.project_id)
                from researchbase.application.approval import ApprovalService

                verifier = ApprovalService(
                    self._factory,
                    self._credentials,
                    LiteratureEvidenceService(self._factory, self._credentials, self._store),
                )
                for grant_id in grants:
                    uow.approval.lock_grant(grant_id)
                    grant, decision, request = verifier._grant_chain(
                        uow, command.project_id, grant_id
                    )
                    verifier._evaluate_in_uow(uow, grant, decision, request, withdrawal=True)
                if repo.related_grants(
                    package["id"], command.project_id
                ) != grants or repo.related_grants(
                    package["id"], command.project_id, contradiction=True
                ):
                    _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "grant scope changed")
            at = self._self_authorize(uow, principal)
            if not withdrawing:
                at = self._stage(uow, principal, command.project_id, parent["id"], _READERS)
            elif retained is None:
                at = self._authorize(uow, principal, command.project_id)
            prior = ExactReference("AuthorConsent", head.id, head.content_hash) if head else None
            repo.insert_consent(
                {
                    "id": command.id,
                    "prepared_submission_version_id": package["id"],
                    "actor_id": principal.actor_id,
                    "consent_state": command.consent_state,
                    "consent_scope": command.consent_scope,
                    "prior_consent_id": command.prior_consent_id,
                    "evidence_artifact_version_id": evidence.id,
                    "captured_at": at,
                    "content_hash": str(
                        sha256_canonical_json(
                            consent_material(
                                package["id"],
                                principal.actor_id,
                                evidence,
                                command.consent_state,
                                prior,
                            )
                        )
                    ),
                    "hash_scheme": "sha256-cjson-v1",
                    "created_at": at,
                    "created_by": principal.actor_id,
                }
            )
            for grant_id in grants:
                uow.approval.terminalize(
                    grant_id,
                    principal.actor_id,
                    "STALE",
                    at,
                    f"author consent withdrawn:{command.id}",
                )
            result = self._consent(
                uow, repo.consent(command.id), command.project_id, metadata_only=True
            )[0]
            repo.force_constraints()
            self._self_authorize(uow, principal)
            if not withdrawing:
                self._context(uow, package, parent, command.project_id, admission=True)
                self._self_authorize(uow, principal)
                self._stage(uow, principal, command.project_id, parent["id"], _READERS)
            elif retained is None:
                self._authorize(uow, principal, command.project_id)
            uow.commit()
            return result

    def _write(self, principal, command, mode) -> Any:
        with self._factory() as uow:
            uow.enable_package_preparation_error_normalization()
            repo = uow.prepared_submission
            repo.prepare_write()
            key = command.id if mode != "withdraw" else command.prepared_submission_version_id
            repo.coordinate(f"b15:{mode}:{key}")
            if mode == "prepare":
                manuscript = repo.manuscript(command.manuscript_version_id, lock=True)
                parent = repo.parent(command.publication_id, lock=True)
                if parent is None:
                    _fail(ErrorCode.NOT_FOUND, "publication unavailable")
                if parent["project_id"] != command.project_id:
                    _fail(ErrorCode.FORBIDDEN, "publication outside requested project")
                if manuscript is None:
                    _fail(ErrorCode.NOT_FOUND, "manuscript unavailable")
                row = {
                    "id": command.id,
                    "publication_id": command.publication_id,
                    "manuscript_version_id": command.manuscript_version_id,
                    "authorship_snapshot_id": command.authorship_snapshot_id,
                }
            else:
                row, parent = self._package(
                    uow, command.prepared_submission_version_id, command.project_id
                )
                repo.manuscript(row["manuscript_version_id"], lock=True)
                parent = repo.parent(row["publication_id"], lock=True)
                row = repo.package(row["id"], lock=True)
            if row is None or parent is None:
                _fail(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "protected package parent unavailable"
                )
            replay = self._compare(uow, principal, command, mode)
            if replay is None and mode == "prepare":
                # Admission precedes material inspection. Fresh checks also run
                # immediately before the effect and after constraints (§12.2).
                self._stage(uow, principal, command.project_id, parent["id"], _WRITERS)
                snapshot = self._snapshot(uow, row, command.project_id, admission=True)
                self._context(uow, row, parent, command.project_id, admission=True)
                projection = self._projection(uow, row["manuscript_version_id"], snapshot.authors)
                version = repo.next_version(parent["id"])
                if version > 2147483647:
                    _fail(ErrorCode.INVALID_STATE_TRANSITION, "package version space exhausted")
                at = self._stage(uow, principal, command.project_id, parent["id"], _WRITERS)
                row.update(
                    version_number=version,
                    status="PREPARED",
                    row_version=1,
                    package_manifest_hash=None,
                    content_hash=None,
                    frozen_at=None,
                    hash_scheme="sha256-cjson-v1",
                    created_at=at,
                    created_by=principal.actor_id,
                )
                repo.insert_package(row)
                for category, ordinal, target in projection:
                    repo.insert_item(
                        {
                            "id": uuid4(),
                            "prepared_submission_version_id": row["id"],
                            "category": category,
                            "ordinal": ordinal,
                            _TARGETS[category][0]: target.id,
                            "created_at": at,
                            "created_by": principal.actor_id,
                        }
                    )
                self._insert_event(repo, row["id"], principal.actor_id, at, None, "PREPARED", None)
            elif replay is None:
                self._structure(uow, row, command.project_id)
                at = self._authorize(uow, principal, command.project_id, frozenset({"OWNER"}))
                repo.withdraw(row["id"], principal.actor_id, at, command.reason)
                self._insert_event(
                    repo, row["id"], principal.actor_id, at, "PREPARED", "WITHDRAWN", command.reason
                )
            if replay is None:
                if mode == "prepare":
                    saved_result = self._readback(uow, row, parent, command.project_id)[0]
                else:
                    saved_result = self._events(uow, repo.package(row["id"]))[-1]
                repo.force_constraints()
                if mode == "withdraw":
                    self._authorize(uow, principal, command.project_id, frozenset({"OWNER"}))
                else:
                    self._stage(
                        uow,
                        principal,
                        command.project_id,
                        parent["id"],
                        _WRITERS if mode == "prepare" else _READERS,
                    )
                uow.commit()
                return saved_result
        # A concurrently completed replay uses exactly the same entitled read path.
        with self._factory() as uow:
            uow.enable_package_preparation_error_normalization()
            uow.begin_formal_read()
            result = self._compare(uow, principal, command, mode)
            self._authorize(uow, principal, command.project_id)
            if result is None:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "committed replay unavailable")
            return result

    @staticmethod
    def _insert_event(repo, package, actor, at, prior, status, reason):
        repo.insert_event(
            {
                "id": uuid4(),
                "prepared_submission_version_id": package,
                "prior_status": prior,
                "new_status": status,
                "actor_id": actor,
                "occurred_at": at,
                "reason": reason,
                "created_at": at,
                "created_by": actor,
            }
        )
