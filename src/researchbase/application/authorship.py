"""Four authenticated S1 methods over immutable, exact authorship facts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, NoReturn
from uuid import UUID, uuid4

from researchbase.application.ports import UnitOfWork
from researchbase.domain.authorship import (
    AuthorshipAuthor,
    ContributionRole,
    ExactReference,
    OrderedContribution,
    authorship_material,
    authorship_sets,
    contribution_material,
    contribution_text,
    uuid_tuple,
    validate_coverage,
)
from researchbase.domain.phase2_identity import CredentialVerifier, VerifiedPrincipal
from researchbase.domain.scientific_conclusion import _uuid
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json

_READERS = frozenset({"OWNER", "RESEARCHER", "REVIEWER", "VIEWER", "APPROVER"})
_WRITERS = frozenset({"OWNER", "RESEARCHER"})


def _fail(code: ErrorCode, message: str) -> NoReturn:
    raise ResearchBaseError(code, message)


def _ids(*ids):
    for identity in ids:
        _uuid(identity, "command identity")


@dataclass(frozen=True, slots=True)
class RecordContributionCommand:
    id: UUID
    project_id: UUID
    publication_id: UUID
    actor_id: UUID
    contribution_role: ContributionRole
    contribution_statement: str

    def __post_init__(self):
        try:
            _ids(self.id, self.project_id, self.publication_id, self.actor_id)
            contribution_material(
                self.publication_id,
                self.actor_id,
                self.contribution_role,
                self.contribution_statement,
                self.actor_id,
            )
            object.__setattr__(
                self, "contribution_statement", contribution_text(self.contribution_statement)
            )
        except (ValueError, TypeError):
            _fail(ErrorCode.VALIDATION_ERROR, "invalid contribution command")


@dataclass(frozen=True, slots=True)
class CreateAuthorshipSnapshotCommand:
    id: UUID
    project_id: UUID
    publication_id: UUID
    author_ids: tuple[UUID, ...]
    corresponding_author_ids: tuple[UUID, ...]
    equal_contribution_groups: tuple[tuple[UUID, ...], ...]
    contribution_record_ids: tuple[UUID, ...]

    def __post_init__(self):
        try:
            _ids(self.id, self.project_id, self.publication_id)
            corresponding, groups = authorship_sets(
                self.author_ids, self.corresponding_author_ids, self.equal_contribution_groups
            )
            uuid_tuple(self.contribution_record_ids, 1, 1000)
            object.__setattr__(self, "corresponding_author_ids", corresponding)
            object.__setattr__(self, "equal_contribution_groups", groups)
        except (ValueError, TypeError):
            _fail(ErrorCode.VALIDATION_ERROR, "invalid authorship snapshot command")


@dataclass(frozen=True, slots=True)
class GetContributionQuery:
    project_id: UUID
    id: UUID

    def __post_init__(self):
        try:
            _ids(self.project_id, self.id)
        except (ValueError, TypeError):
            _fail(ErrorCode.VALIDATION_ERROR, "invalid exact record query")


@dataclass(frozen=True, slots=True)
class GetAuthorshipSnapshotQuery:
    project_id: UUID
    id: UUID

    def __post_init__(self):
        try:
            _ids(self.project_id, self.id)
        except (ValueError, TypeError):
            _fail(ErrorCode.VALIDATION_ERROR, "invalid exact record query")


@dataclass(frozen=True, slots=True)
class ContributionReadback:
    id: UUID
    project_id: UUID
    publication_id: UUID
    actor_id: UUID
    contribution_role: ContributionRole
    contribution_statement: str
    recorded_by: UUID
    created_at: datetime
    content_hash: str
    hash_scheme: Literal["sha256-cjson-v1"]


@dataclass(frozen=True, slots=True)
class AuthorshipSnapshotReadback:
    id: UUID
    project_id: UUID
    publication_id: UUID
    authors: tuple[AuthorshipAuthor, ...]
    corresponding_author_ids: tuple[UUID, ...]
    equal_contribution_groups: tuple[tuple[UUID, ...], ...]
    contributions: tuple[OrderedContribution, ...]
    created_by: UUID
    created_at: datetime
    content_hash: str
    hash_scheme: Literal["sha256-cjson-v1"]


class AuthorshipService:
    def __init__(self, factory: Callable[[], UnitOfWork], credentials: CredentialVerifier):
        self._factory = factory
        self._credentials = credentials

    def _authenticate(self, principal, at):
        if type(principal) is not VerifiedPrincipal:
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        try:
            live = principal.verified_at <= at and self._credentials.is_valid(principal, at)
        except Exception:
            live = False
        if not live:
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "live verified credential required")

    def _boundary(self, principal, value, expected):
        # Authenticate before any target lookup; final authority uses DB time below.
        self._authenticate(principal, datetime.now(UTC))
        if type(value) is not expected:
            _fail(ErrorCode.VALIDATION_ERROR, "closed command or query required")

    def _authorize(self, repo, principal, project, roles):
        rows = repo.authority(principal, project)
        at = repo.at()
        self._authenticate(principal, at)
        for row in rows:
            if (
                row["retired_at"] is None
                and row["membership_status"] == "ACTIVE"
                and row["started_at"] <= at
                and row["binding_status"] == "ACTIVE"
                and row["role"] in roles
                and row["effective_from"] <= at
                and (row["effective_until"] is None or at < row["effective_until"])
                and row["bound_at"] <= at
                and (row["revoked_at"] is None or at < row["revoked_at"])
                and (roles == _READERS or row["lifecycle_status"] == "ACTIVE")
            ):
                return at
        _fail(ErrorCode.FORBIDDEN, "current project entitlement required")

    @staticmethod
    def _scoped(repo, row, project):
        if row is None:
            _fail(ErrorCode.NOT_FOUND, "exact record unavailable")
        publication = repo.publication(row["publication_id"])
        if publication is None or publication["project_id"] != project:
            _fail(ErrorCode.FORBIDDEN, "record outside requested project")

    def _contribution(self, repo, row, project):
        self._scoped(repo, row, project)
        try:
            digest = str(
                sha256_canonical_json(
                    contribution_material(
                        row["publication_id"],
                        row["actor_id"],
                        row["contribution_role"],
                        row["contribution_statement"],
                        row["recorded_by"],
                    )
                )
            )
            if (
                digest != row["content_hash"]
                or row["hash_scheme"] != "sha256-cjson-v1"
                or row["recorded_by"] != row["created_by"]
                or contribution_text(row["contribution_statement"]) != row["contribution_statement"]
            ):
                raise ValueError("corrupt contribution")
            return ContributionReadback(
                row["id"],
                project,
                row["publication_id"],
                row["actor_id"],
                row["contribution_role"],
                row["contribution_statement"],
                row["recorded_by"],
                row["created_at"],
                row["content_hash"],
                row["hash_scheme"],
            )
        except (KeyError, TypeError, ValueError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved contribution material invalid")

    def _snapshot(self, repo, row, project):
        self._scoped(repo, row, project)
        relations = repo.snapshot_relations(row["id"])
        try:
            authors = tuple(
                AuthorshipAuthor(a["actor_id"], a["ordinal"]) for a in relations["authors"]
            )
            corresponding_rows = relations["corresponding_authors"]
            if [a["ordinal"] for a in corresponding_rows] != list(range(len(corresponding_rows))):
                raise ValueError("invalid coordinates")
            corresponding = tuple(a["actor_id"] for a in corresponding_rows)
            grouped = {}
            for member in relations["equal_groups"]:
                group = grouped.setdefault(member["group_ordinal"], [])
                if member["ordinal"] != len(group):
                    raise ValueError("invalid group coordinates")
                group.append(member["actor_id"])
            if sorted(grouped) != list(range(len(grouped))):
                raise ValueError("invalid group coordinates")
            groups = tuple(tuple(grouped[index]) for index in sorted(grouped))
            contributions = []
            material = []
            for link in relations["contributions"]:
                saved = repo.contribution(link["contribution_record_id"])
                if saved is None or saved["publication_id"] != row["publication_id"]:
                    raise ValueError("missing same publication contribution")
                result = self._contribution(repo, saved, project)
                contributions.append(
                    OrderedContribution(
                        ExactReference("ContributionRecord", result.id, result.content_hash),
                        link["ordinal"],
                    )
                )
                material.append(saved)
            actor_types = {
                a.actor_id: (repo.actor(a.actor_id) or {}).get("actor_type") for a in authors
            }
            validate_coverage(
                tuple(a.actor_id for a in authors), actor_types, row["publication_id"], material
            )
            corresponding, groups = authorship_sets(
                tuple(a.actor_id for a in authors), corresponding, groups
            )
            digest = str(
                sha256_canonical_json(
                    authorship_material(
                        row["publication_id"], authors, corresponding, groups, tuple(contributions)
                    )
                )
            )
            if digest != row["content_hash"] or row["hash_scheme"] != "sha256-cjson-v1":
                raise ValueError("corrupt snapshot")
            return AuthorshipSnapshotReadback(
                row["id"],
                project,
                row["publication_id"],
                authors,
                corresponding,
                groups,
                tuple(contributions),
                row["created_by"],
                row["created_at"],
                row["content_hash"],
                row["hash_scheme"],
            )
        except (KeyError, TypeError, ValueError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved snapshot material invalid")

    def _attempts(self, action) -> Any:
        for attempt in range(3):
            try:
                return action()
            except ResearchBaseError as error:
                if getattr(error, "_authorship_retryable", False) and attempt < 2:
                    continue
                raise ResearchBaseError(error.code, error.message) from None
        raise AssertionError("unreachable retry")

    def record_contribution(
        self, principal: VerifiedPrincipal, command: RecordContributionCommand
    ) -> ContributionReadback:
        self._boundary(principal, command, RecordContributionCommand)
        return self._attempts(lambda: self._create(principal, command, snapshot=False))

    def create_authorship_snapshot(
        self, principal: VerifiedPrincipal, command: CreateAuthorshipSnapshotCommand
    ) -> AuthorshipSnapshotReadback:
        self._boundary(principal, command, CreateAuthorshipSnapshotCommand)
        return self._attempts(lambda: self._create(principal, command, snapshot=True))

    def _create(self, principal, command, *, snapshot):
        with self._factory() as uow:
            uow.enable_authorship_error_normalization()
            repo = uow.authorship
            repo.lock_request(command.id)
            self._authenticate(principal, repo.at())
            publication = repo.lock_publication(command.publication_id, command.project_id)
            repo.lock_snapshot()
            repo.lock_project(command.project_id)
            self._authorize(repo, principal, command.project_id, _READERS)
            # Immutable records can be read to discover the required actor lock IDs;
            # all selected material is reread after the ordered locks.
            selected = (
                [repo.contribution(identity) for identity in command.contribution_record_ids]
                if snapshot
                else []
            )
            actors = {principal.actor_id}
            if snapshot:
                actors.update(command.author_ids)
                for row in selected:
                    if row:
                        actors.update((row["actor_id"], row["recorded_by"]))
            else:
                actors.add(command.actor_id)
            repo.lock_actors(actors)
            if snapshot:
                repo.lock_contributions(command.contribution_record_ids)
            self._authorize(repo, principal, command.project_id, _READERS)
            saved = repo.snapshot(command.id) if snapshot else repo.contribution(command.id)
            if saved is not None:
                self._scoped(repo, saved, command.project_id)
                if saved["created_by"] != principal.actor_id:
                    _fail(ErrorCode.FORBIDDEN, "saved recorder differs")
                result: Any = (
                    self._snapshot(repo, saved, command.project_id)
                    if snapshot
                    else self._contribution(repo, saved, command.project_id)
                )
                matching = result.publication_id == command.publication_id
                if snapshot:
                    matching = (
                        matching and tuple(a.actor_id for a in result.authors) == command.author_ids
                    )
                    matching = (
                        matching
                        and result.corresponding_author_ids == command.corresponding_author_ids
                    )
                    matching = (
                        matching
                        and result.equal_contribution_groups == command.equal_contribution_groups
                    )
                    matching = (
                        matching
                        and tuple(c.contribution_record.id for c in result.contributions)
                        == command.contribution_record_ids
                    )
                else:
                    matching = matching and (
                        result.actor_id,
                        result.contribution_role,
                        result.contribution_statement,
                    ) == (
                        command.actor_id,
                        command.contribution_role,
                        command.contribution_statement,
                    )
                if not matching:
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "saved request material conflicts")
                self._authorize(repo, principal, command.project_id, _READERS)
                return result
            self._authorize(repo, principal, command.project_id, _WRITERS)
            if publication is None:
                foreign = repo.publication(command.publication_id)
                _fail(
                    ErrorCode.FORBIDDEN if foreign else ErrorCode.NOT_FOUND,
                    "publication unavailable",
                )
            if snapshot:
                selected = [
                    repo.contribution(identity) for identity in command.contribution_record_ids
                ]
                for row in selected:
                    self._contribution(repo, row, command.project_id)
                types = {}
                for identity in command.author_ids:
                    actor = repo.actor(identity)
                    if actor is None or actor["retired_at"] is not None:
                        _fail(ErrorCode.VALIDATION_ERROR, "eligible HUMAN author required")
                    types[identity] = actor["actor_type"]
                try:
                    validate_coverage(command.author_ids, types, command.publication_id, selected)
                except ValueError:
                    _fail(
                        ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                        "invalid author contribution coverage",
                    )
                authors = tuple(
                    AuthorshipAuthor(identity, index + 1)
                    for index, identity in enumerate(command.author_ids)
                )
                contributions = tuple(
                    OrderedContribution(
                        ExactReference("ContributionRecord", row["id"], row["content_hash"]), index
                    )
                    for index, row in enumerate(selected)
                )
                digest = str(
                    sha256_canonical_json(
                        authorship_material(
                            command.publication_id,
                            authors,
                            command.corresponding_author_ids,
                            command.equal_contribution_groups,
                            contributions,
                        )
                    )
                )
            else:
                actor = repo.actor(command.actor_id)
                if actor is None or actor["retired_at"] is not None:
                    _fail(ErrorCode.VALIDATION_ERROR, "eligible attributed actor required")
                digest = str(
                    sha256_canonical_json(
                        contribution_material(
                            command.publication_id,
                            command.actor_id,
                            command.contribution_role,
                            command.contribution_statement,
                            principal.actor_id,
                        )
                    )
                )
            at = self._authorize(repo, principal, command.project_id, _WRITERS)
            row = {
                "id": command.id,
                "publication_id": command.publication_id,
                "created_by": principal.actor_id,
                "created_at": at,
                "content_hash": digest,
                "hash_scheme": "sha256-cjson-v1",
            }
            if snapshot:
                repo.insert_snapshot(row)
                base = {
                    "authorship_snapshot_id": command.id,
                    "created_by": principal.actor_id,
                    "created_at": at,
                }

                def relation(**fields):
                    return {**base, "id": uuid4(), **fields}

                repo.insert_snapshot_relations(
                    {
                        "authors": [
                            relation(actor_id=a.actor_id, ordinal=a.ordinal) for a in authors
                        ],
                        "corresponding_authors": [
                            relation(actor_id=a, ordinal=i)
                            for i, a in enumerate(command.corresponding_author_ids)
                        ],
                        "equal_groups": [
                            relation(actor_id=a, group_ordinal=g, ordinal=i)
                            for g, group in enumerate(command.equal_contribution_groups)
                            for i, a in enumerate(group)
                        ],
                        "contributions": [
                            relation(
                                contribution_record_id=c.contribution_record.id, ordinal=c.ordinal
                            )
                            for c in contributions
                        ],
                    }
                )
            else:
                repo.insert_contribution(
                    {
                        **row,
                        "actor_id": command.actor_id,
                        "recorded_by": principal.actor_id,
                        "contribution_role": command.contribution_role,
                        "contribution_statement": command.contribution_statement,
                    }
                )
            result = (
                self._snapshot(repo, row, command.project_id)
                if snapshot
                else self._contribution(repo, repo.contribution(command.id), command.project_id)
            )
            self._authorize(repo, principal, command.project_id, _WRITERS)
            uow.commit()
            return result

    def get_contribution(
        self, principal: VerifiedPrincipal, query: GetContributionQuery
    ) -> ContributionReadback:
        self._boundary(principal, query, GetContributionQuery)
        return self._attempts(lambda: self._get(principal, query, snapshot=False))

    def get_authorship_snapshot(
        self, principal: VerifiedPrincipal, query: GetAuthorshipSnapshotQuery
    ) -> AuthorshipSnapshotReadback:
        self._boundary(principal, query, GetAuthorshipSnapshotQuery)
        return self._attempts(lambda: self._get(principal, query, snapshot=True))

    def _get(self, principal, query, *, snapshot):
        with self._factory() as uow:
            uow.enable_authorship_error_normalization()
            repo = uow.authorship
            repo.prepare_read()
            self._authorize(repo, principal, query.project_id, _READERS)
            row = repo.snapshot(query.id) if snapshot else repo.contribution(query.id)
            result = (
                self._snapshot(repo, row, query.project_id)
                if snapshot
                else self._contribution(repo, row, query.project_id)
            )
            self._authorize(repo, principal, query.project_id, _READERS)
            return result
