"""Authenticated R2 ScientificConclusion commands over exact typed references."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, NoReturn
from uuid import UUID, uuid4

from researchbase.application.ports import UnitOfWork
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.scientific_conclusion import (
    ClaimConclusionInput,
    LiteratureConclusionInput,
    conclusion_content_material,
    conclusion_support_material,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json

_WRITERS = frozenset({"OWNER", "RESEARCHER"})
_READERS = frozenset({"OWNER", "RESEARCHER", "REVIEWER", "VIEWER", "APPROVER"})
_RELATIONS = frozenset({"SUPPORTS", "CONTRADICTS", "QUALIFIES"})


def _fail(code: ErrorCode, message: str) -> NoReturn:
    raise ResearchBaseError(code, message)


@dataclass(frozen=True, slots=True)
class ClaimInputRequest:
    claim_version_id: UUID
    relation_type: str
    literature_support_snapshot_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class LiteratureInputRequest:
    literature_evidence_id: UUID
    relation_type: str


@dataclass(frozen=True, slots=True)
class ConclusionCommandResult:
    conclusion_id: UUID
    version_id: UUID


@dataclass(frozen=True, slots=True)
class ConclusionReadback:
    conclusion_id: UUID
    version_id: UUID
    project_id: UUID
    version_number: int
    status: str
    statement: str
    scope: dict[str, str | None]
    confidence: str
    limitation_summary: str | None
    claim_inputs: tuple[ClaimConclusionInput, ...]
    literature_inputs: tuple[LiteratureConclusionInput, ...]
    support_material: dict[str, object] | None
    content_material: dict[str, object] | None
    support_set_hash: str | None
    content_hash: str | None
    validity: str


class ScientificConclusionService:
    def __init__(
        self, factory: Callable[[], UnitOfWork], credentials: Any, literature_evidence: Any
    ) -> None:
        self._factory = factory
        self._credentials = credentials
        # The accepted M3 service validates source bytes, review history and snapshot hashes
        # against the same UoW. It cannot be replaced by caller-provided proof material.
        self._literature = literature_evidence

    def record_internal_scientific_release(self, principal, command):
        """The immutable receipt is the local release fact; no scientific material changes."""
        from researchbase.application.approval import ApprovalService

        return ApprovalService(self._factory, self._credentials, self._literature)._release(
            principal, command
        )

    def _authorize(
        self,
        uow: UnitOfWork,
        principal: VerifiedPrincipal,
        project: UUID,
        roles: frozenset[str],
    ):
        if not isinstance(principal, VerifiedPrincipal) or type(project) is not UUID:
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        uow.literature_search_plan.lock_project(project)
        rows = uow.literature_search_plan.authorize(principal, project)
        at = uow.source_version.at()
        try:
            live = principal.verified_at <= at and self._credentials.is_valid(principal, at)
        except Exception:
            live = False
        if live and (roles == _READERS or uow.literature_search_plan.project_active(project)):
            for row in rows:
                if (
                    row["actor_type"] == "HUMAN"
                    and row["retired_at"] is None
                    and row["membership_status"] == "ACTIVE"
                    and row["binding_status"] == "ACTIVE"
                    and row["role"] in roles
                    and row["effective_from"] <= at
                    and (row["effective_until"] is None or at < row["effective_until"])
                    and row["bound_at"] <= at
                    and (row["revoked_at"] is None or at < row["revoked_at"])
                ):
                    return at
        _fail(ErrorCode.FORBIDDEN, "current authenticated project authority unavailable")

    @staticmethod
    def _validated_requests(
        claims: tuple[ClaimInputRequest, ...],
        literature: tuple[LiteratureInputRequest, ...],
    ) -> None:
        if (
            not isinstance(claims, tuple)
            or not isinstance(literature, tuple)
            or len(claims) > 100
            or len(literature) > 100
            or any(
                not isinstance(x, ClaimInputRequest)
                or type(x.claim_version_id) is not UUID
                or x.relation_type not in _RELATIONS
                or (
                    x.literature_support_snapshot_id is not None
                    and type(x.literature_support_snapshot_id) is not UUID
                )
                for x in claims
            )
            or any(
                not isinstance(x, LiteratureInputRequest)
                or type(x.literature_evidence_id) is not UUID
                or x.relation_type not in _RELATIONS
                for x in literature
            )
            or len({(x.claim_version_id, x.relation_type) for x in claims}) != len(claims)
            or len({(x.literature_evidence_id, x.relation_type) for x in literature})
            != len(literature)
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "bounded unique typed R2 inputs required")

    @staticmethod
    def _retry(operation: Callable[[], Any]):
        for attempt in range(3):
            try:
                return operation()
            except ResearchBaseError as exc:
                if exc.code is not ErrorCode.CONCURRENT_MODIFICATION or attempt == 2:
                    raise
        raise AssertionError("unreachable retry loop")

    def _receipt(self, principal, project, command, request, digest, result, at):
        return {
            "id": uuid4(),
            "deployment_id": principal.deployment_id,
            "project_id": project,
            "actor_id": principal.actor_id,
            "command_name": command,
            "request_id": request,
            "input_hash": digest,
            "result_conclusion_id": result.conclusion_id,
            "result_version_id": result.version_id,
            "completed_at": at,
        }

    def _claim(
        self,
        uow,
        project,
        request: ClaimInputRequest,
        ordinal: int,
        *,
        require_current: bool = True,
    ):
        row = uow.scientific_conclusion.claim_reference(request.claim_version_id, project)
        if row is None or row["status"] not in {"FROZEN", "SUPERSEDED"}:
            _fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "frozen same-project claim required")
        target = self._literature._target(uow, "ClaimVersion", request.claim_version_id, project)
        if target["content_hash"] != row["content_hash"] or (
            require_current and target["current_validity"] != "VALID"
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "claim closure is not valid")
        snapshot_hash = None
        if request.literature_support_snapshot_id is not None:
            snapshot = uow.scientific_conclusion.snapshot_reference(
                request.literature_support_snapshot_id, project
            )
            if snapshot is None or snapshot["claim_version_id"] != request.claim_version_id:
                _fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "snapshot must bind exact claim")
            checked = self._literature._snapshot(
                uow, request.literature_support_snapshot_id, project
            )
            if checked["content_hash"] != snapshot["content_hash"] or (
                require_current and checked["validity"] != "VALID"
            ):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "snapshot closure is not valid")
            snapshot_hash = snapshot["content_hash"]
        return ClaimConclusionInput(
            request.claim_version_id,
            row["content_hash"],
            request.relation_type,
            ordinal,
            request.literature_support_snapshot_id,
            snapshot_hash,
        )

    def _evidence(
        self,
        uow,
        project,
        request: LiteratureInputRequest,
        ordinal: int,
        *,
        author: UUID | None = None,
        require_current: bool = True,
    ):
        row = uow.scientific_conclusion.evidence_reference(request.literature_evidence_id, project)
        if row is None:
            _fail(ErrorCode.NOT_FOUND, "same-project literature evidence required")
        checked = self._literature._read(uow, request.literature_evidence_id, project)
        if checked["content_hash"] != row["content_hash"] or (
            require_current and checked["source_validity"] != "VALID"
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "literature source closure invalid")
        if require_current and request.relation_type == "SUPPORTS":
            events = checked["review_events"]
            if (
                checked["review_status"] != "VERIFIED"
                or not events
                or events[-1]["new_status"] != "VERIFIED"
                or events[-1]["reviewed_by"] in {checked["created_by"], author}
            ):
                _fail(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "positive direct support requires independent current review",
                )
        elif require_current and checked["review_status"] in {"DISPUTED", "REJECTED"}:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "disputed evidence is not current")
        return LiteratureConclusionInput(
            request.literature_evidence_id, row["content_hash"], request.relation_type, ordinal
        )

    def create(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        statement: str,
        scope: dict[str, str | None],
        confidence: str,
        limitation_summary: str | None,
        claims: tuple[ClaimInputRequest, ...],
        literature: tuple[LiteratureInputRequest, ...],
        request_id: UUID,
    ) -> ConclusionCommandResult:
        return self._create(
            principal,
            project,
            None,
            statement,
            scope,
            confidence,
            limitation_summary,
            claims,
            literature,
            request_id,
        )

    def revise(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        conclusion_id: UUID,
        statement: str,
        scope: dict[str, str | None],
        confidence: str,
        limitation_summary: str | None,
        claims: tuple[ClaimInputRequest, ...],
        literature: tuple[LiteratureInputRequest, ...],
        request_id: UUID,
    ) -> ConclusionCommandResult:
        if type(conclusion_id) is not UUID:
            _fail(ErrorCode.VALIDATION_ERROR, "conclusion UUID required")
        return self._create(
            principal,
            project,
            conclusion_id,
            statement,
            scope,
            confidence,
            limitation_summary,
            claims,
            literature,
            request_id,
        )

    def _create(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        conclusion_id: UUID | None,
        statement: str,
        scope: dict[str, str | None],
        confidence: str,
        limitation_summary: str | None,
        claims: tuple[ClaimInputRequest, ...],
        literature: tuple[LiteratureInputRequest, ...],
        request_id: UUID,
    ) -> ConclusionCommandResult:
        if type(request_id) is not UUID:
            _fail(ErrorCode.VALIDATION_ERROR, "request UUID required")
        self._validated_requests(claims, literature)
        # Validate the exact own material before opening a write transaction.
        seed_id = UUID(int=0)
        try:
            material = conclusion_content_material(
                seed_id, statement, scope, confidence, limitation_summary, "0" * 64
            )
        except ValueError as exc:
            _fail(ErrorCode.VALIDATION_ERROR, str(exc))
        command = "CREATE_CONCLUSION" if conclusion_id is None else "REVISE_CONCLUSION"
        digest = str(
            sha256_canonical_json(
                {
                    "command": command,
                    "project_id": str(project),
                    "conclusion_id": str(conclusion_id) if conclusion_id else None,
                    "material": material,
                    "claims": [
                        [
                            str(x.claim_version_id),
                            x.relation_type,
                            str(x.literature_support_snapshot_id)
                            if x.literature_support_snapshot_id
                            else None,
                        ]
                        for x in claims
                    ],
                    "literature": [
                        [str(x.literature_evidence_id), x.relation_type] for x in literature
                    ],
                }
            )
        )

        def once():
            with self._factory() as uow:
                uow.enable_serializable_retry_normalization()
                uow.begin_serializable()
                at = self._authorize(uow, principal, project, _WRITERS)
                repo = uow.scientific_conclusion
                repo.lock_command(
                    principal.deployment_id, project, principal.actor_id, command, request_id
                )
                prior = repo.receipt(principal, project, command, request_id)
                if prior:
                    if prior["input_hash"] != digest:
                        _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "conclusion request replay conflicts")
                    result = ConclusionCommandResult(
                        prior["result_conclusion_id"], prior["result_version_id"]
                    )
                else:
                    claim_rows = tuple(
                        self._claim(uow, project, x, i) for i, x in enumerate(claims)
                    )
                    literature_rows = tuple(
                        self._evidence(uow, project, x, i, author=principal.actor_id)
                        for i, x in enumerate(literature)
                    )
                    if conclusion_id is None:
                        parent_id = uuid4()
                        version_number = 1
                        repo.insert_conclusion(
                            {
                                "id": parent_id,
                                "project_id": project,
                                "current_version_id": None,
                                "created_by": principal.actor_id,
                                "created_at": at,
                                "row_version": 1,
                            }
                        )
                    else:
                        parent_id = conclusion_id
                        parent = repo.conclusion(parent_id, project, lock=True)
                        if parent is None or parent["current_version_id"] is None:
                            _fail(
                                ErrorCode.INVALID_STATE_TRANSITION,
                                "revision requires current frozen version",
                            )
                        current = repo.version(parent["current_version_id"], parent_id)
                        if (
                            current is None
                            or current["status"] != "FROZEN"
                            or repo.draft_version(parent_id) is not None
                        ):
                            _fail(
                                ErrorCode.INVALID_STATE_TRANSITION,
                                "revision requires one current frozen version",
                            )
                        version_number = repo.next_version_number(parent_id)
                    version_id = uuid4()
                    result = ConclusionCommandResult(parent_id, version_id)
                    repo.insert_version(
                        {
                            "id": version_id,
                            "scientific_conclusion_id": parent_id,
                            "version_number": version_number,
                            "status": "DRAFT",
                            "statement": material["statement"],
                            "scope": material["scope"],
                            "confidence": confidence,
                            "limitation_summary": material["limitation_summary"],
                            "support_set_hash": None,
                            "content_hash": None,
                            "hash_scheme": "sha256-cjson-v1",
                            "created_by": principal.actor_id,
                            "created_at": at,
                            "frozen_at": None,
                            "row_version": 1,
                        }
                    )
                    for x in claim_rows:
                        repo.insert_claim_input(
                            {
                                "conclusion_version_id": version_id,
                                "claim_version_id": x.claim_version_id,
                                "literature_support_snapshot_id": x.literature_support_snapshot_id,
                                "relation_type": x.relation_type,
                                "ordinal": x.ordinal,
                            }
                        )
                    for x in literature_rows:
                        repo.insert_literature_input(
                            {
                                "conclusion_version_id": version_id,
                                "literature_evidence_id": x.literature_evidence_id,
                                "relation_type": x.relation_type,
                                "ordinal": x.ordinal,
                            }
                        )
                    repo.save_receipt(
                        self._receipt(principal, project, command, request_id, digest, result, at)
                    )
                self._authorize(uow, principal, project, _WRITERS)
                uow.commit()
                return result

        return self._retry(once)

    def replace_inputs(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        conclusion_id: UUID,
        version_id: UUID,
        claims: tuple[ClaimInputRequest, ...],
        literature: tuple[LiteratureInputRequest, ...],
        request_id: UUID,
    ) -> ConclusionCommandResult:
        if any(type(x) is not UUID for x in (conclusion_id, version_id, request_id)):
            _fail(ErrorCode.VALIDATION_ERROR, "exact conclusion and request UUIDs required")
        self._validated_requests(claims, literature)
        digest = str(
            sha256_canonical_json(
                {
                    "command": "REPLACE_INPUTS",
                    "project_id": str(project),
                    "conclusion_id": str(conclusion_id),
                    "version_id": str(version_id),
                    "claims": [
                        [
                            str(x.claim_version_id),
                            x.relation_type,
                            str(x.literature_support_snapshot_id)
                            if x.literature_support_snapshot_id
                            else None,
                        ]
                        for x in claims
                    ],
                    "literature": [
                        [str(x.literature_evidence_id), x.relation_type] for x in literature
                    ],
                }
            )
        )

        def once():
            with self._factory() as uow:
                uow.enable_serializable_retry_normalization()
                uow.begin_serializable()
                at = self._authorize(uow, principal, project, _WRITERS)
                repo = uow.scientific_conclusion
                repo.lock_command(
                    principal.deployment_id,
                    project,
                    principal.actor_id,
                    "REPLACE_INPUTS",
                    request_id,
                )
                prior = repo.receipt(principal, project, "REPLACE_INPUTS", request_id)
                if prior:
                    if prior["input_hash"] != digest:
                        _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "conclusion request replay conflicts")
                    result = ConclusionCommandResult(
                        prior["result_conclusion_id"], prior["result_version_id"]
                    )
                else:
                    parent = repo.conclusion(conclusion_id, project, lock=True)
                    version = repo.version(version_id, conclusion_id, lock=True) if parent else None
                    if version is None or version["status"] != "DRAFT":
                        _fail(
                            ErrorCode.INVALID_STATE_TRANSITION,
                            "only a current draft input set may change",
                        )
                    claim_rows = tuple(
                        self._claim(uow, project, x, i) for i, x in enumerate(claims)
                    )
                    literature_rows = tuple(
                        self._evidence(uow, project, x, i, author=version["created_by"])
                        for i, x in enumerate(literature)
                    )
                    repo.clear_draft_inputs(version_id)
                    for x in claim_rows:
                        repo.insert_claim_input(
                            {
                                "conclusion_version_id": version_id,
                                "claim_version_id": x.claim_version_id,
                                "literature_support_snapshot_id": x.literature_support_snapshot_id,
                                "relation_type": x.relation_type,
                                "ordinal": x.ordinal,
                            }
                        )
                    for x in literature_rows:
                        repo.insert_literature_input(
                            {
                                "conclusion_version_id": version_id,
                                "literature_evidence_id": x.literature_evidence_id,
                                "relation_type": x.relation_type,
                                "ordinal": x.ordinal,
                            }
                        )
                    result = ConclusionCommandResult(conclusion_id, version_id)
                    repo.save_receipt(
                        self._receipt(
                            principal, project, "REPLACE_INPUTS", request_id, digest, result, at
                        )
                    )
                self._authorize(uow, principal, project, _WRITERS)
                uow.commit()
                return result

        return self._retry(once)

    def _view(self, uow, project, conclusion_id, version_id, *, require_current=False):
        repo = uow.scientific_conclusion
        parent = repo.conclusion(conclusion_id, project)
        version = repo.version(version_id, conclusion_id) if parent else None
        if parent is None or version is None:
            _fail(ErrorCode.NOT_FOUND, "scientific conclusion version not found")
        claim_rows = repo.claim_inputs(version_id)
        literature_rows = repo.literature_inputs(version_id)
        claims = tuple(
            self._claim(
                uow,
                project,
                ClaimInputRequest(
                    x["claim_version_id"], x["relation_type"], x["literature_support_snapshot_id"]
                ),
                x["ordinal"],
                require_current=require_current,
            )
            for x in claim_rows
        )
        literature = tuple(
            self._evidence(
                uow,
                project,
                LiteratureInputRequest(x["literature_evidence_id"], x["relation_type"]),
                x["ordinal"],
                author=version["created_by"],
                require_current=require_current,
            )
            for x in literature_rows
        )
        validity = "VALID"
        if not require_current:
            for item in claims:
                target = self._literature._target(
                    uow, "ClaimVersion", item.claim_version_id, project
                )
                if target["current_validity"] != "VALID":
                    validity = target["current_validity"]
                if item.literature_support_snapshot_id is not None:
                    snapshot = self._literature._snapshot(
                        uow, item.literature_support_snapshot_id, project
                    )
                    if snapshot["validity"] != "VALID":
                        validity = snapshot["validity"]
            for item in literature:
                evidence = self._literature._read(uow, item.literature_evidence_id, project)
                if (
                    evidence["source_validity"] != "VALID"
                    or evidence["review_status"] in {"DISPUTED", "REJECTED"}
                    or (
                        item.relation_type == "SUPPORTS" and evidence["review_status"] != "VERIFIED"
                    )
                ):
                    validity = "STALE"
        support = content = None
        if version["status"] in {"FROZEN", "SUPERSEDED"}:
            for item in literature:
                if item.relation_type != "SUPPORTS":
                    continue
                evidence = self._literature._read(uow, item.literature_evidence_id, project)
                prior_events = [
                    event
                    for event in evidence["review_events"]
                    if event["reviewed_at"] <= version["frozen_at"]
                ]
                if (
                    not prior_events
                    or prior_events[-1]["new_status"] != "VERIFIED"
                    or prior_events[-1]["reviewed_by"]
                    in {evidence["created_by"], version["created_by"]}
                    or not repo.human_actor(prior_events[-1]["reviewed_by"])
                ):
                    _fail(
                        ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                        "frozen direct support lacked independent human review",
                    )
            try:
                support = conclusion_support_material(claims, literature)
                support_hash = str(sha256_canonical_json(support))
                content = conclusion_content_material(
                    conclusion_id,
                    version["statement"],
                    version["scope"],
                    version["confidence"],
                    version["limitation_summary"],
                    support_hash,
                )
            except ValueError as exc:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, str(exc))
            if (
                support_hash != version["support_set_hash"]
                or str(sha256_canonical_json(content)) != version["content_hash"]
            ):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "conclusion hash mismatch")
        return ConclusionReadback(
            conclusion_id,
            version_id,
            project,
            version["version_number"],
            version["status"],
            version["statement"],
            version["scope"],
            version["confidence"],
            version["limitation_summary"],
            claims,
            literature,
            support,
            content,
            version["support_set_hash"],
            version["content_hash"],
            validity,
        )

    def freeze(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        conclusion_id: UUID,
        version_id: UUID,
        request_id: UUID,
    ) -> ConclusionCommandResult:
        if any(type(x) is not UUID for x in (conclusion_id, version_id, request_id)):
            _fail(ErrorCode.VALIDATION_ERROR, "exact conclusion and request UUIDs required")
        digest = str(
            sha256_canonical_json(
                {
                    "command": "FREEZE_CONCLUSION",
                    "project_id": str(project),
                    "conclusion_id": str(conclusion_id),
                    "version_id": str(version_id),
                }
            )
        )

        def once():
            with self._factory() as uow:
                uow.enable_serializable_retry_normalization()
                uow.begin_serializable()
                at = self._authorize(uow, principal, project, _WRITERS)
                repo = uow.scientific_conclusion
                repo.lock_command(
                    principal.deployment_id,
                    project,
                    principal.actor_id,
                    "FREEZE_CONCLUSION",
                    request_id,
                )
                prior = repo.receipt(principal, project, "FREEZE_CONCLUSION", request_id)
                if prior:
                    if prior["input_hash"] != digest:
                        _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "conclusion request replay conflicts")
                    result = ConclusionCommandResult(
                        prior["result_conclusion_id"], prior["result_version_id"]
                    )
                else:
                    parent = repo.conclusion(conclusion_id, project, lock=True)
                    version = repo.version(version_id, conclusion_id, lock=True) if parent else None
                    if version is None or version["status"] != "DRAFT":
                        _fail(ErrorCode.INVALID_STATE_TRANSITION, "only a draft can be frozen")
                    previous = parent["current_version_id"]
                    if previous is not None:
                        prior_version = repo.version(previous, conclusion_id)
                        if (
                            prior_version is None
                            or prior_version["status"] != "FROZEN"
                            or version["version_number"] != prior_version["version_number"] + 1
                        ):
                            _fail(
                                ErrorCode.INVALID_STATE_TRANSITION,
                                "draft does not follow current frozen version",
                            )
                    view = self._view(uow, project, conclusion_id, version_id, require_current=True)
                    try:
                        support = conclusion_support_material(
                            view.claim_inputs, view.literature_inputs
                        )
                        support_hash = str(sha256_canonical_json(support))
                        content = conclusion_content_material(
                            conclusion_id,
                            view.statement,
                            view.scope,
                            view.confidence,
                            view.limitation_summary,
                            support_hash,
                        )
                    except ValueError as exc:
                        _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, str(exc))
                    repo.freeze(
                        conclusion_id,
                        version_id,
                        principal.actor_id,
                        at,
                        support_hash,
                        str(sha256_canonical_json(content)),
                        previous,
                    )
                    result = ConclusionCommandResult(conclusion_id, version_id)
                    repo.save_receipt(
                        self._receipt(
                            principal, project, "FREEZE_CONCLUSION", request_id, digest, result, at
                        )
                    )
                self._authorize(uow, principal, project, _WRITERS)
                uow.commit()
                return result

        return self._retry(once)

    def read(
        self, principal: VerifiedPrincipal, project: UUID, conclusion_id: UUID, version_id: UUID
    ) -> ConclusionReadback:
        with self._factory() as uow:
            self._authorize(uow, principal, project, _READERS)
            return self._view(uow, project, conclusion_id, version_id)
