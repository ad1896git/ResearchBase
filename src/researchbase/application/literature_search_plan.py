"""Application commands for authoring and freezing literature search plans."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

from researchbase.application.ports import UnitOfWork
from researchbase.domain.literature_search_plan import (
    FrozenResearchQuestionReference,
    LiteratureSearchPlanMaterial,
    LiteratureSearchPlanStatus,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.research import ResearchQuestionVersion
from researchbase.foundation.canonical_json import canonical_json_text
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.frozen_json import thaw_json
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.versioning import VersionStatus


class SearchPlanCredentialVerifier(Protocol):
    def is_valid(self, principal: VerifiedPrincipal, at: datetime) -> bool: ...


@dataclass(frozen=True, slots=True)
class CreateLiteratureSearchPlan:
    principal: VerifiedPrincipal
    project_id: UUID
    material: LiteratureSearchPlanMaterial
    request_id: UUID


@dataclass(frozen=True, slots=True)
class UpdateLiteratureSearchPlanDraft:
    principal: VerifiedPrincipal
    project_id: UUID
    plan_id: UUID
    version_id: UUID
    material: LiteratureSearchPlanMaterial
    request_id: UUID


@dataclass(frozen=True, slots=True)
class ReviseLiteratureSearchPlan:
    principal: VerifiedPrincipal
    project_id: UUID
    plan_id: UUID
    base_version_id: UUID
    request_id: UUID


@dataclass(frozen=True, slots=True)
class EditLiteratureSearchPlanQuestions:
    principal: VerifiedPrincipal
    project_id: UUID
    plan_id: UUID
    version_id: UUID
    research_question_version_id: UUID
    request_id: UUID


@dataclass(frozen=True, slots=True)
class RemoveLiteratureSearchPlanQuestion:
    principal: VerifiedPrincipal
    project_id: UUID
    plan_id: UUID
    version_id: UUID
    research_question_id: UUID
    request_id: UUID


@dataclass(frozen=True, slots=True)
class TransitionLiteratureSearchPlanVersion:
    principal: VerifiedPrincipal
    project_id: UUID
    plan_id: UUID
    version_id: UUID
    request_id: UUID


class LiteratureSearchPlanService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        credential_verifier: SearchPlanCredentialVerifier | None,
    ) -> None:
        self._uow_factory = uow_factory
        self._credential_verifier = credential_verifier

    def create(self, command: CreateLiteratureSearchPlan) -> dict[str, object]:
        return self._retry(lambda: self._create_once(command))

    def _create_once(self, command: CreateLiteratureSearchPlan) -> dict[str, object]:
        material = command.material
        name = "CREATE_LITERATURE_SEARCH_PLAN"
        request = _material_request(command.project_id, material)
        request["research_question_version_ids"] = [
            str(ref.version_id)
            for ref in sorted(
                material.research_question_refs,
                key=lambda ref: (str(ref.research_question_id), str(ref.version_id)),
            )
        ]
        digest = str(sha256_canonical_json(request))
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.literature_search_plan
            repo.lock_project(command.project_id)
            repo.lock_command(
                command.principal.deployment_id,
                command.principal.actor_id,
                command.project_id,
                name,
                command.request_id,
            )
            refs = self._resolve_refs(repo, command.project_id, material.research_question_refs)
            if not repo.project_active(command.project_id):
                raise _error(ErrorCode.FORBIDDEN, "project is not active")
            facts, at = self._authorize(repo, command.principal, command.project_id)
            _require_writer(facts)
            prior = repo.receipt(command.principal, command.project_id, name, command.request_id)
            if prior:
                return _replay(prior, digest)
            plan_id = uuid4()
            version_id = uuid4()
            repo.insert_plan(
                {
                    "id": plan_id,
                    "project": command.project_id,
                    "actor": command.principal.actor_id,
                    "at": at,
                }
            )
            repo.insert_version(
                _version_values(version_id, plan_id, 1, command.principal.actor_id, at, material)
            )
            repo.replace_questions(version_id, [row["version_id"] for row in refs])
            dto = _dto(plan_id, version_id, 1, LiteratureSearchPlanStatus.DRAFT, None)
            _save_receipt(
                repo,
                command.principal,
                command.project_id,
                name,
                command.request_id,
                digest,
                plan_id,
                version_id,
                dto,
                at,
            )
            uow.commit()
            return dto

    def update(self, command: UpdateLiteratureSearchPlanDraft) -> dict[str, object]:
        request = _material_request(command.project_id, command.material) | {
            "plan_id": str(command.plan_id),
            "version_id": str(command.version_id),
        }
        return self._edit(
            command.principal,
            command.project_id,
            command.plan_id,
            command.version_id,
            "UPDATE_LITERATURE_SEARCH_PLAN_DRAFT",
            command.request_id,
            request,
            [ref.version_id for ref in command.material.research_question_refs],
            lambda repo, at: self._do_update(repo, command, at),
        )

    def add_question(self, command: EditLiteratureSearchPlanQuestions) -> dict[str, object]:
        request = {
            "project_id": str(command.project_id),
            "plan_id": str(command.plan_id),
            "version_id": str(command.version_id),
            "research_question_version_id": str(command.research_question_version_id),
        }
        return self._edit(
            command.principal,
            command.project_id,
            command.plan_id,
            command.version_id,
            "ADD_LITERATURE_SEARCH_PLAN_QUESTION",
            command.request_id,
            request,
            [command.research_question_version_id],
            lambda repo, at: self._do_add(repo, command, at),
        )

    def remove_question(self, command: RemoveLiteratureSearchPlanQuestion) -> dict[str, object]:
        request = {
            "project_id": str(command.project_id),
            "plan_id": str(command.plan_id),
            "version_id": str(command.version_id),
            "research_question_id": str(command.research_question_id),
        }
        return self._edit(
            command.principal,
            command.project_id,
            command.plan_id,
            command.version_id,
            "REMOVE_LITERATURE_SEARCH_PLAN_QUESTION",
            command.request_id,
            request,
            [],
            lambda repo, at: self._do_remove(repo, command, at),
        )

    def freeze(self, command: TransitionLiteratureSearchPlanVersion) -> dict[str, object]:
        return self._transition(command, "FREEZE_LITERATURE_SEARCH_PLAN", freeze=True)

    def abandon(self, command: TransitionLiteratureSearchPlanVersion) -> dict[str, object]:
        return self._transition(command, "ABANDON_LITERATURE_SEARCH_PLAN", freeze=False)

    def get(
        self, principal: VerifiedPrincipal, project_id: UUID, plan_id: UUID
    ) -> dict[str, object]:
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.literature_search_plan
            plan = repo.plan(plan_id, project_id)
            if plan is None:
                raise _error(ErrorCode.NOT_FOUND, "literature search plan not found")
            self._authorize(repo, principal, project_id, require_writer=False)
            versions = [self._read_version(repo, project_id, row) for row in repo.versions(plan_id)]
            current = str(plan["current_version_id"]) if plan["current_version_id"] else None
            uow.commit()
            return {
                "plan_id": str(plan_id),
                "project_id": str(project_id),
                "current_version_id": current,
                "versions": versions,
            }

    def list(self, principal: VerifiedPrincipal, project_id: UUID) -> list[dict[str, object]]:
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.literature_search_plan
            self._authorize(repo, principal, project_id, require_writer=False)
            result = []
            for plan in repo.plans(project_id):
                result.append(
                    {
                        "plan_id": str(plan["id"]),
                        "project_id": str(project_id),
                        "current_version_id": str(plan["current_version_id"])
                        if plan["current_version_id"]
                        else None,
                        "versions": [
                            self._read_version(repo, project_id, row)
                            for row in repo.versions(plan["id"])
                        ],
                    }
                )
            uow.commit()
            return result

    def _read_version(self, repo, project_id, row):
        refs = repo.question_refs(row["id"])
        for ref in refs:
            _validate_question_row(ref, project_id)
        dto = _dto(
            row["plan_id"],
            row["id"],
            row["version_number"],
            LiteratureSearchPlanStatus(row["status"]),
            row["content_hash"],
        )
        dto.update(
            {
                "objective": row["objective"],
                "source_scope": row["source_scope"],
                "inclusion_criteria": row["inclusion_criteria"],
                "exclusion_criteria": row["exclusion_criteria"],
                "time_range": row["time_range"],
                "language_scope": row["language_scope"],
                "search_strategy": row["search_strategy"],
                "planned_providers": row["planned_providers"],
                "stopping_rule": row["stopping_rule"],
                "research_question_refs": [
                    {
                        "research_question_id": str(r["research_question_id"]),
                        "version_id": str(r["version_id"]),
                        "content_hash": r["content_hash"],
                    }
                    for r in refs
                ],
            }
        )
        return dto

    def revise(self, command: ReviseLiteratureSearchPlan) -> dict[str, object]:
        return self._retry(lambda: self._revise_once(command))

    def _revise_once(self, command: ReviseLiteratureSearchPlan) -> dict[str, object]:
        name = "REVISE_LITERATURE_SEARCH_PLAN"
        request = {
            "project_id": str(command.project_id),
            "plan_id": str(command.plan_id),
            "base_version_id": str(command.base_version_id),
        }
        digest = str(sha256_canonical_json(request))
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.literature_search_plan
            repo.lock_project(command.project_id)
            repo.lock_command(
                command.principal.deployment_id,
                command.principal.actor_id,
                command.project_id,
                name,
                command.request_id,
            )
            plan = repo.plan(command.plan_id, command.project_id, lock=True)
            base = repo.version(command.base_version_id, lock=True)
            if plan is None or base is None or base["plan_id"] != command.plan_id:
                raise _error(ErrorCode.NOT_FOUND, "literature search plan not found")
            prior = repo.receipt(command.principal, command.project_id, name, command.request_id)
            if prior:
                facts, _ = self._authorize(repo, command.principal, command.project_id)
                _require_writer(facts)
                return _replay(prior, digest)
            if plan["current_version_id"] != base["id"] or base["status"] not in {
                "FROZEN",
                "SUPERSEDED",
            }:
                raise _error(
                    ErrorCode.INVALID_STATE_TRANSITION,
                    "revision requires the current frozen version",
                )
            if any(v["status"] == "DRAFT" for v in repo.versions(command.plan_id)):
                raise _error(ErrorCode.INVALID_STATE_TRANSITION, "a draft version already exists")
            refs = repo.question_refs(base["id"])
            for ref in refs:
                repo.question(ref["version_id"], lock=True)
            repo.lock_question_inputs(base["id"])
            refs = repo.question_refs(base["id"])
            refs = self._resolve_rows(repo, command.project_id, refs)
            version_id = uuid4()
            number = repo.next_number(command.plan_id)
            if not repo.project_active(command.project_id):
                raise _error(ErrorCode.FORBIDDEN, "project is not active")
            facts, at = self._authorize(repo, command.principal, command.project_id)
            _require_writer(facts)
            material = _material_from_rows(repo, command.project_id, base, refs)
            repo.insert_version(
                _version_values(
                    version_id, command.plan_id, number, command.principal.actor_id, at, material
                )
            )
            repo.replace_questions(version_id, [r["version_id"] for r in refs])
            dto = _dto(command.plan_id, version_id, number, LiteratureSearchPlanStatus.DRAFT, None)
            _save_receipt(
                repo,
                command.principal,
                command.project_id,
                name,
                command.request_id,
                digest,
                command.plan_id,
                version_id,
                dto,
                at,
            )
            uow.commit()
            return dto

    def _edit(
        self,
        principal,
        project_id,
        plan_id,
        version_id,
        name,
        request_id,
        request,
        required_question_versions,
        effect,
    ):
        return self._retry(
            lambda: self._edit_once(
                principal,
                project_id,
                plan_id,
                version_id,
                name,
                request_id,
                request,
                required_question_versions,
                effect,
            )
        )

    def _edit_once(
        self,
        principal,
        project_id,
        plan_id,
        version_id,
        name,
        request_id,
        request,
        required_question_versions,
        effect,
    ):
        digest = str(sha256_canonical_json(request))
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.literature_search_plan
            repo.lock_project(project_id)
            repo.lock_command(
                principal.deployment_id, principal.actor_id, project_id, name, request_id
            )
            plan = repo.plan(plan_id, project_id, lock=True)
            version = repo.version(version_id, lock=True)
            if plan is None or version is None or version["plan_id"] != plan_id:
                raise _error(ErrorCode.NOT_FOUND, "literature search plan not found")
            existing = repo.question_refs(version_id)
            question_ids = {row["version_id"] for row in existing} | set(required_question_versions)
            question_rows = [repo.question(question_id) for question_id in question_ids]
            for row in sorted(
                (row for row in question_rows if row is not None),
                key=lambda item: (str(item["research_question_id"]), str(item["version_id"])),
            ):
                repo.question(row["version_id"], lock=True)
            repo.lock_question_inputs(version_id)
            existing = repo.question_refs(version_id)
            self._resolve_rows(repo, project_id, existing)
            if not repo.project_active(project_id):
                raise _error(ErrorCode.FORBIDDEN, "project is not active")
            facts, at = self._authorize(repo, principal, project_id)
            _require_writer(facts)
            prior = repo.receipt(principal, project_id, name, request_id)
            if prior:
                return _replay(prior, digest)
            if version["status"] != "DRAFT":
                raise _error(
                    ErrorCode.SEARCH_PLAN_VERSION_IMMUTABLE,
                    "only a draft plan version may be edited",
                )
            result = effect(repo, at)
            _save_receipt(
                repo,
                principal,
                project_id,
                name,
                request_id,
                digest,
                plan_id,
                version_id,
                result,
                at,
            )
            uow.commit()
            return result

    def _do_update(self, repo, command, at):
        if command.material.plan_id != command.plan_id:
            raise _error(
                ErrorCode.VALIDATION_ERROR, "material plan identity does not match command scope"
            )
        if command.material.research_question_refs:
            raise _error(
                ErrorCode.VALIDATION_ERROR,
                "question relations must use the dedicated add/remove commands",
            )
        repo.update_draft(command.version_id, _material_values(command.material))
        return _dto(
            command.plan_id,
            command.version_id,
            repo.version(command.version_id)["version_number"],
            LiteratureSearchPlanStatus.DRAFT,
            None,
        )

    def _do_add(self, repo, command, at):
        row = repo.question(command.research_question_version_id, lock=True)
        if row is None:
            raise _error(
                ErrorCode.SEARCH_PLAN_QUESTION_INVALID, "ResearchQuestion version is unavailable"
            )
        _validate_question_row(row, command.project_id)
        existing = repo.question_refs(command.version_id)
        if any(r["research_question_id"] == row["research_question_id"] for r in existing):
            raise _error(ErrorCode.VALIDATION_ERROR, "ResearchQuestion identity already attached")
        repo.add_question(command.version_id, command.research_question_version_id, len(existing))
        repo.canonicalize_questions(command.version_id)
        version = repo.version(command.version_id)
        return _dto(
            command.plan_id,
            command.version_id,
            version["version_number"],
            LiteratureSearchPlanStatus.DRAFT,
            None,
        )

    def _do_remove(self, repo, command, at):
        if not repo.remove_question(command.version_id, command.research_question_id):
            raise _error(ErrorCode.SEARCH_PLAN_QUESTION_INVALID, "ResearchQuestion is not attached")
        version = repo.version(command.version_id)
        return _dto(
            command.plan_id,
            command.version_id,
            version["version_number"],
            LiteratureSearchPlanStatus.DRAFT,
            None,
        )

    def _transition(self, command, name, *, freeze):
        return self._retry(lambda: self._transition_once(command, name, freeze=freeze))

    def _transition_once(self, command, name, *, freeze):
        request = {
            "project_id": str(command.project_id),
            "plan_id": str(command.plan_id),
            "version_id": str(command.version_id),
        }
        digest = str(sha256_canonical_json(request))
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.literature_search_plan
            repo.lock_project(command.project_id)
            repo.lock_command(
                command.principal.deployment_id,
                command.principal.actor_id,
                command.project_id,
                name,
                command.request_id,
            )
            plan = repo.plan(command.plan_id, command.project_id, lock=True)
            version = repo.version(command.version_id)
            if plan is None or version is None or version["plan_id"] != command.plan_id:
                raise _error(ErrorCode.NOT_FOUND, "literature search plan not found")
            prior = repo.receipt(command.principal, command.project_id, name, command.request_id)
            if prior:
                facts, _ = self._authorize(repo, command.principal, command.project_id)
                _require_writer(facts)
                return _replay(prior, digest)
            if version["status"] != "DRAFT":
                raise _error(ErrorCode.SEARCH_PLAN_VERSION_IMMUTABLE, "only a draft can transition")
            refs = []
            if freeze:
                version_ids = [command.version_id]
                if plan["current_version_id"] is not None:
                    version_ids.append(plan["current_version_id"])
                repo.lock_versions(sorted(version_ids, key=str))
                version = repo.version(command.version_id)
                refs = self._resolve_rows(
                    repo, command.project_id, repo.question_refs(command.version_id)
                )
                repo.lock_question_inputs(command.version_id)
                refs = self._resolve_rows(
                    repo, command.project_id, repo.question_refs(command.version_id)
                )
            else:
                repo.lock_versions([command.version_id])
                version = repo.version(command.version_id)
            if version is None or version["status"] != "DRAFT":
                raise _error(ErrorCode.SEARCH_PLAN_VERSION_IMMUTABLE, "only a draft can transition")
            if not repo.project_active(command.project_id):
                raise _error(ErrorCode.FORBIDDEN, "project is not active")
            facts, at = self._authorize(repo, command.principal, command.project_id)
            _require_writer(facts)
            if not freeze:
                repo.abandon(command.version_id)
                dto = _dto(
                    command.plan_id,
                    command.version_id,
                    version["version_number"],
                    LiteratureSearchPlanStatus.ABANDONED,
                    None,
                )
            else:
                if not refs:
                    raise _error(
                        ErrorCode.SEARCH_PLAN_QUESTION_REQUIRED,
                        "at least one ResearchQuestion is required to freeze",
                    )
                material = _material_from_rows(repo, command.project_id, version, refs)
                if material.language_scope is None:
                    raise _error(
                        ErrorCode.SEARCH_PLAN_LANGUAGE_SCOPE_REQUIRED,
                        "language_scope is required to freeze",
                    )
                content_hash = material.digest()
                repo.freeze(command.version_id, content_hash, at)
                if plan["current_version_id"] is not None:
                    repo.supersede(plan["current_version_id"])
                repo.set_current(command.plan_id, command.version_id)
                dto = _dto(
                    command.plan_id,
                    command.version_id,
                    version["version_number"],
                    LiteratureSearchPlanStatus.FROZEN,
                    content_hash,
                )
            _save_receipt(
                repo,
                command.principal,
                command.project_id,
                name,
                command.request_id,
                digest,
                command.plan_id,
                command.version_id,
                dto,
                at,
            )
            uow.commit()
            return dto

    def _resolve_refs(self, repo, project_id, refs):
        rows = []
        for ref in sorted(
            refs, key=lambda item: (str(item.research_question_id), str(item.version_id))
        ):
            row = repo.question(ref.version_id, lock=True)
            if (
                row is None
                or row["research_question_id"] != ref.research_question_id
                or row["content_hash"] != ref.content_hash
            ):
                raise _error(
                    ErrorCode.SEARCH_PLAN_QUESTION_INVALID, "ResearchQuestion reference is invalid"
                )
            _validate_question_row(row, project_id)
            rows.append(row)
        return sorted(rows, key=lambda row: (str(row["version_id"]), row["content_hash"]))

    def _validate_refs(self, repo, project_id, refs):
        self._resolve_refs(repo, project_id, refs)

    def _resolve_rows(self, repo, project_id, rows):
        resolved = []
        seen = set()
        for raw in rows:
            row = repo.question(raw["version_id"], lock=True)
            if row is None:
                raise _error(
                    ErrorCode.SEARCH_PLAN_QUESTION_INVALID,
                    "ResearchQuestion reference is unavailable",
                )
            _validate_question_row(row, project_id)
            if row["research_question_id"] in seen:
                raise _error(
                    ErrorCode.SEARCH_PLAN_QUESTION_INVALID, "duplicate ResearchQuestion identity"
                )
            seen.add(row["research_question_id"])
            resolved.append(row)
        return sorted(resolved, key=lambda row: (str(row["version_id"]), row["content_hash"]))

    def _authorize(self, repo, principal, project_id, *, require_writer=True):
        # Lock the complete history before sampling fresh authorization time.
        candidates = repo.authorize(principal, project_id)
        at = repo.at()
        verifier = self._credential_verifier
        try:
            valid = bool(verifier and verifier.is_valid(principal, at))
        except Exception:
            valid = False
        if valid and principal.verified_at <= at:
            for facts in candidates:
                if (
                    facts["actor_type"] in {"HUMAN", "AGENT"}
                    and facts["retired_at"] is None
                    and facts["membership_status"] == "ACTIVE"
                    and facts["role"]
                    in (
                        {"OWNER", "RESEARCHER"}
                        if require_writer
                        else {"OWNER", "RESEARCHER", "REVIEWER", "APPROVER", "VIEWER"}
                    )
                    and facts["effective_from"] <= at
                    and (facts["effective_until"] is None or at < facts["effective_until"])
                    and facts["binding_status"] == "ACTIVE"
                    and facts["bound_at"] <= at
                    and (facts["revoked_at"] is None or at < facts["revoked_at"])
                ):
                    return facts, at
        raise _error(ErrorCode.FORBIDDEN, "current project authority is unavailable")

    @staticmethod
    def _retry[ResultT](call: Callable[[], ResultT]) -> ResultT:
        for attempt in range(3):
            try:
                return call()
            except ResearchBaseError as exc:
                if exc.code is not ErrorCode.CONCURRENT_MODIFICATION or attempt == 2:
                    raise
                time.sleep(0.01 * (attempt + 1))
        raise AssertionError("retry loop must return or raise")


def _validate_question_row(row, project_id):
    if row["project_id"] != project_id:
        raise _error(
            ErrorCode.SEARCH_PLAN_QUESTION_SCOPE_MISMATCH,
            "ResearchQuestion must belong to this project",
        )
    if (
        row["status"] not in {"FROZEN", "SUPERSEDED"}
        or row["content_hash"] is None
        or row["frozen_at"] is None
    ):
        raise _error(
            ErrorCode.SEARCH_PLAN_QUESTION_INVALID, "ResearchQuestion version must be frozen"
        )
    try:
        question = ResearchQuestionVersion(
            id=row["version_id"],
            research_question_id=row["research_question_id"],
            version_number=row["version_number"],
            status=VersionStatus(row["status"]),
            question_text=row["question_text"],
            scope=row["scope"],
            rationale=row["rationale"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            content_hash=row["content_hash"],
            hash_scheme=row["hash_scheme"],
            frozen_at=row["frozen_at"],
            row_version=row["row_version"],
        )
    except (TypeError, ValueError) as exc:
        raise _error(
            ErrorCode.SEARCH_PLAN_QUESTION_INVALID, "ResearchQuestion hash verification failed"
        ) from exc
    if question.content_hash != row["content_hash"]:
        raise _error(
            ErrorCode.SEARCH_PLAN_QUESTION_INVALID, "ResearchQuestion hash verification failed"
        )


def _material_from_rows(repo, project_id, version, refs=None):
    raw_refs = refs if refs is not None else repo.question_refs(version["id"])
    typed_refs = tuple(
        FrozenResearchQuestionReference(
            r["research_question_id"], r["version_id"], r["content_hash"]
        )
        for r in raw_refs
    )
    language = version["language_scope"]
    if isinstance(language, str):
        language = json.loads(language)
    return LiteratureSearchPlanMaterial(
        plan_id=version["plan_id"],
        research_question_refs=typed_refs,
        objective=version["objective"],
        source_scope=version["source_scope"],
        inclusion_criteria=version["inclusion_criteria"],
        exclusion_criteria=version["exclusion_criteria"],
        time_range=_parse_time_range(version["time_range"]),
        language_scope=tuple(language) if language is not None else None,
        search_strategy=version["search_strategy"],
        planned_providers=tuple(_json_list(version["planned_providers"])),
        stopping_rule=version["stopping_rule"],
    )


def _parse_time_range(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = json.loads(value)
    from datetime import date

    return {
        key: date.fromisoformat(value[key]) if value[key] else None for key in ("from", "through")
    }


def _json_list(value):
    return json.loads(value) if isinstance(value, str) else value


def _material_values(material):
    payload = material.payload() if material.language_scope is not None else None

    def serial(value):
        return canonical_json_text(_plain_json(value)) if value is not None else None

    return {
        "objective": material.objective,
        "source_scope": material.source_scope.value,
        "inclusion": serial(
            payload["inclusion_criteria"] if payload else material.inclusion_criteria
        ),
        "exclusion": serial(
            payload["exclusion_criteria"] if payload else material.exclusion_criteria
        ),
        "time_range": serial(payload["time_range"] if payload else material.time_range),
        "language_scope": serial(
            list(material.language_scope) if material.language_scope is not None else None
        ),
        "strategy": material.search_strategy.value,
        "providers": serial(list(material.planned_providers)),
        "stopping": serial(payload["stopping_rule"] if payload else material.stopping_rule),
    }


def _version_values(version_id, plan_id, number, actor, at, material):
    return {
        "id": version_id,
        "plan": plan_id,
        "number": number,
        "actor": actor,
        "at": at,
        **_material_values(material),
    }


def _material_request(project_id, material):
    payload = material.payload() if material.language_scope is not None else None
    return {
        "project_id": str(project_id),
        "objective": material.objective,
        "source_scope": material.source_scope.value,
        "inclusion_criteria": payload["inclusion_criteria"]
        if payload
        else _plain_json(material.inclusion_criteria),
        "exclusion_criteria": payload["exclusion_criteria"]
        if payload
        else _plain_json(material.exclusion_criteria),
        "time_range": payload["time_range"] if payload else _plain_json(material.time_range),
        "language_scope": list(material.language_scope)
        if material.language_scope is not None
        else None,
        "search_strategy": material.search_strategy.value,
        "planned_providers": list(material.planned_providers),
        "stopping_rule": payload["stopping_rule"]
        if payload
        else _plain_json(material.stopping_rule),
    }


def _plain_json(value):
    return thaw_json(value) if value is not None else None


def _dto(plan_id, version_id, number, status, content_hash):
    return {
        "plan_id": str(plan_id),
        "version_id": str(version_id),
        "version_number": number,
        "status": status.value,
        "content_hash": content_hash,
    }


def _save_receipt(repo, principal, project, command, request, digest, plan, version, dto, at):
    repo.insert_receipt(
        {
            "id": uuid4(),
            "deployment": principal.deployment_id,
            "actor": principal.actor_id,
            "project": project,
            "command": command,
            "request": request,
            "hash": digest,
            "plan": plan,
            "version": version,
            "dto": canonical_json_text(dto),
            "at": at,
        }
    )


def _replay(prior, digest):
    if prior["request_hash"] != digest:
        raise _error(
            ErrorCode.IDEMPOTENCY_CONFLICT, "request ID was used with different command material"
        )
    value = prior["result_dto"]
    return json.loads(value) if isinstance(value, str) else dict(value)


def _require_writer(facts):
    if facts["role"] not in {"OWNER", "RESEARCHER"}:
        raise _error(ErrorCode.FORBIDDEN, "project write role is required")


def _error(code, message):
    return ResearchBaseError(code, message)
