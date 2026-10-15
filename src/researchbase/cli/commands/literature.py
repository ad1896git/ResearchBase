"""CLI transport for PR2-01 LiteratureSource and SourceIdentifier commands."""

# Typer command declarations use Option descriptors as parameter defaults.
# ruff: noqa: B008

from __future__ import annotations

import json
from datetime import date
from uuid import UUID

import typer

from researchbase.application.literature_search_plan import (
    CreateLiteratureSearchPlan,
    EditLiteratureSearchPlanQuestions,
    RemoveLiteratureSearchPlanQuestion,
    ReviseLiteratureSearchPlan,
    TransitionLiteratureSearchPlanVersion,
    UpdateLiteratureSearchPlanDraft,
)
from researchbase.application.novelty import (
    ExactReadQuery,
    RecordNoveltyAssessmentCommand,
    RecordPriorArtRelationCommand,
    RecordSearchCoverageCommand,
)
from researchbase.application.source_identity import (
    AddSourceIdentifier,
    RegisterLiteratureSource,
    RejectSourceIdentifier,
    VerifySourceIdentifier,
)
from researchbase.application.source_merge import (
    DecideSourceMerge,
    ProposeSourceMerge,
    RevokeSourceMergeApproval,
)
from researchbase.application.source_merge_execution import ConsumeSourceMergeProposal
from researchbase.application.source_version import (
    CreateSourceVersion,
    TransitionSourceVersion,
    UpdateSourceVersionDraft,
)
from researchbase.domain.literature_search_plan import (
    FrozenResearchQuestionReference,
    LiteratureSearchPlanMaterial,
    LiteratureSearchStrategy,
    LiteratureSourceScope,
)
from researchbase.domain.novelty import NoveltyOutcome, PriorArtKind
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.source_identity import IdentifierType, SourceKind
from researchbase.domain.source_version import (
    FrozenSourceReference,
    SourceVersionKind,
    SourceVersionMaterial,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

from ..common import invoke
from ..context import CliRuntime
from ..errors import INTERNAL_ERROR_EXIT_CODE, cli_exit_code
from ..output import emit_error, emit_success
from ..transport import add_command, command_group


def _runtime(ctx: typer.Context) -> CliRuntime:
    runtime = ctx.find_root().obj
    if not isinstance(runtime, CliRuntime):
        raise RuntimeError("CLI runtime is not initialized")
    return runtime


def _principal(runtime: CliRuntime) -> VerifiedPrincipal:
    principal = getattr(runtime.services, "verified_principal", None)
    if not isinstance(principal, VerifiedPrincipal):
        raise ResearchBaseError(
            ErrorCode.AUTHENTICATION_REQUIRED,
            "a trusted verified principal is unavailable to the CLI",
        )
    if runtime.actor_id is not None and runtime.actor_id != principal.actor_id:
        raise ResearchBaseError(
            ErrorCode.FORBIDDEN, "--actor-id does not match the authenticated principal"
        )
    return principal


def _literature(runtime: CliRuntime):
    service = getattr(runtime.services, "literature", None)
    if service is None:
        raise ResearchBaseError(ErrorCode.AUTHENTICATION_REQUIRED, "literature service unavailable")
    return service


def _source_merge(runtime: CliRuntime):
    service = getattr(runtime.services, "source_merge", None)
    if service is None:
        raise ResearchBaseError(
            ErrorCode.AUTHENTICATION_REQUIRED, "source merge service unavailable"
        )
    return service


def _request_id(runtime: CliRuntime) -> UUID:
    if not runtime.request_id_supplied:
        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR, "--request-id is required for literature writes"
        )
    return runtime.request_id


def _uuid(value: str | None, option: str) -> UUID:
    try:
        if value is None:
            raise ValueError
        return UUID(value)
    except (TypeError, ValueError) as exc:
        raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, f"{option} must be a UUID") from exc


def _run(runtime: CliRuntime, json_mode: bool, operation):
    try:
        emit_success(operation(), json_mode)
    except ResearchBaseError as exc:
        emit_error(exc, runtime.request_id, json_mode)
        raise typer.Exit(code=cli_exit_code(exc)) from None


def source_create(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    kind: SourceKind = typer.Option(..., "--kind"),
    title: str = typer.Option(..., "--title"),
    initial_identifier_type: IdentifierType | None = typer.Option(
        None, "--initial-identifier-type"
    ),
    initial_identifier_value: str | None = typer.Option(None, "--initial-identifier-value"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _literature(runtime).register_literature_source(
            RegisterLiteratureSource(
                _principal(runtime),
                _uuid(project_id, "--project-id"),
                kind,
                title,
                _request_id(runtime),
                initial_identifier_type,
                initial_identifier_value,
            )
        ),
    )


def source_merge_propose(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    source_a_id: str = typer.Option(..., "--source-a-id"),
    source_b_id: str = typer.Option(..., "--source-b-id"),
    canonical_survivor_id: str = typer.Option(..., "--canonical-survivor-id"),
    rationale: str = typer.Option(..., "--rationale"),
    evidence_artifact_ids: list[str] = typer.Option([], "--evidence-artifact-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _source_merge(runtime).propose(
            ProposeSourceMerge(
                _principal(runtime),
                _uuid(project_id, "--project-id"),
                _uuid(source_a_id, "--source-a-id"),
                _uuid(source_b_id, "--source-b-id"),
                _uuid(canonical_survivor_id, "--canonical-survivor-id"),
                rationale,
                _request_id(runtime),
                None,
                tuple(_uuid(value, "--evidence-artifact-id") for value in evidence_artifact_ids),
            )
        ),
    )


def source_merge_supersede(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    prior_proposal_id: str = typer.Option(..., "--prior-proposal-id"),
    source_a_id: str = typer.Option(..., "--source-a-id"),
    source_b_id: str = typer.Option(..., "--source-b-id"),
    canonical_survivor_id: str = typer.Option(..., "--canonical-survivor-id"),
    rationale: str = typer.Option(..., "--rationale"),
    evidence_artifact_ids: list[str] = typer.Option([], "--evidence-artifact-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _source_merge(runtime).propose(
            ProposeSourceMerge(
                _principal(runtime),
                _uuid(project_id, "--project-id"),
                _uuid(source_a_id, "--source-a-id"),
                _uuid(source_b_id, "--source-b-id"),
                _uuid(canonical_survivor_id, "--canonical-survivor-id"),
                rationale,
                _request_id(runtime),
                _uuid(prior_proposal_id, "--prior-proposal-id"),
                tuple(_uuid(value, "--evidence-artifact-id") for value in evidence_artifact_ids),
            )
        ),
    )


def source_merge_show(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    proposal_id: str = typer.Option(..., "--proposal-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _source_merge(runtime).get(
            _principal(runtime),
            _uuid(project_id, "--project-id"),
            _uuid(proposal_id, "--proposal-id"),
        ),
    )


def _source_merge_decide(
    ctx: typer.Context,
    project_id: str,
    proposal_id: str,
    decision: str,
    reason: str | None,
    json_mode: bool,
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _source_merge(runtime).decide(
            DecideSourceMerge(
                _principal(runtime),
                _uuid(project_id, "--project-id"),
                _uuid(proposal_id, "--proposal-id"),
                decision,
                _request_id(runtime),
                reason,
            )
        ),
    )


def source_merge_approve(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    proposal_id: str = typer.Option(..., "--proposal-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    _source_merge_decide(ctx, project_id, proposal_id, "APPROVE", None, json_mode)


def source_merge_reject(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    proposal_id: str = typer.Option(..., "--proposal-id"),
    reason: str = typer.Option(..., "--reason"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    _source_merge_decide(ctx, project_id, proposal_id, "REJECT", reason, json_mode)


def source_merge_revoke(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    proposal_id: str = typer.Option(..., "--proposal-id"),
    reason: str = typer.Option(..., "--reason"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)

    def revoke():
        _source_merge(runtime).revoke(
            RevokeSourceMergeApproval(
                _principal(runtime),
                _uuid(project_id, "--project-id"),
                _uuid(proposal_id, "--proposal-id"),
                reason,
                _request_id(runtime),
            )
        )
        return {"status": "REVOKED"}

    _run(runtime, json_mode, revoke)


def source_show(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    source_id: str = typer.Option(..., "--source-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _literature(runtime).get_literature_source(
            _principal(runtime), _uuid(project_id, "--project-id"), _uuid(source_id, "--source-id")
        ),
    )


def source_merge_execute(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    proposal_id: str = typer.Option(..., "--proposal-id"),
    proposal_basis_hash: str = typer.Option(..., "--proposal-basis-hash"),
    identity_basis_artifact_id: str = typer.Option(..., "--identity-basis-artifact-id"),
    identity_basis_content_hash: str = typer.Option(..., "--identity-basis-content-hash"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _source_merge_execution(runtime).consume(
            ConsumeSourceMergeProposal(
                _principal(runtime),
                _uuid(project_id, "--project-id"),
                _uuid(proposal_id, "--proposal-id"),
                proposal_basis_hash,
                FrozenSourceReference(
                    _uuid(identity_basis_artifact_id, "--identity-basis-artifact-id"),
                    identity_basis_content_hash,
                ),
                _request_id(runtime),
            )
        ),
    )


def source_resolve(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    identifier_type: IdentifierType = typer.Option(..., "--identifier-type"),
    value: str = typer.Option(..., "--value"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _literature(runtime).find_source_by_identifier(
            _principal(runtime), _uuid(project_id, "--project-id"), identifier_type, value
        ),
    )


def identifier_add(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    source_id: str = typer.Option(..., "--source-id"),
    identifier_type: IdentifierType = typer.Option(..., "--identifier-type"),
    identifier_value: str = typer.Option(..., "--value"),
    is_primary: bool = typer.Option(False, "--primary"),
    binding_basis_artifact_version_id: str | None = typer.Option(
        None, "--binding-basis-artifact-version-id"
    ),
    supersedes_rejected_identifier_id: str | None = typer.Option(
        None, "--supersedes-rejected-identifier-id"
    ),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _literature(runtime).add_source_identifier(
            AddSourceIdentifier(
                _principal(runtime),
                _uuid(project_id, "--project-id"),
                _uuid(source_id, "--source-id"),
                identifier_type,
                identifier_value,
                is_primary,
                _request_id(runtime),
                UUID(binding_basis_artifact_version_id)
                if binding_basis_artifact_version_id
                else None,
                UUID(supersedes_rejected_identifier_id)
                if supersedes_rejected_identifier_id
                else None,
            )
        ),
    )


def _status_command(
    ctx: typer.Context,
    project_id: str,
    identifier_id: str,
    basis_id: str,
    reason: str,
    json_mode: bool,
    *,
    reject: bool,
) -> None:
    runtime = _runtime(ctx)
    command_type = RejectSourceIdentifier if reject else VerifySourceIdentifier
    _run(
        runtime,
        json_mode,
        lambda: getattr(
            _literature(runtime),
            "reject_source_identifier" if reject else "verify_source_identifier",
        )(
            command_type(
                _principal(runtime),
                _uuid(project_id, "--project-id"),
                _uuid(identifier_id, "--identifier-id"),
                _uuid(basis_id, "--basis-artifact-version-id"),
                reason,
                _request_id(runtime),
            )
        ),
    )


def identifier_verify(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    identifier_id: str = typer.Option(..., "--identifier-id"),
    basis_artifact_version_id: str = typer.Option(..., "--basis-artifact-version-id"),
    reason: str = typer.Option(..., "--reason"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    _status_command(
        ctx, project_id, identifier_id, basis_artifact_version_id, reason, json_mode, reject=False
    )


def identifier_reject(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    identifier_id: str = typer.Option(..., "--identifier-id"),
    basis_artifact_version_id: str = typer.Option(..., "--basis-artifact-version-id"),
    reason: str = typer.Option(..., "--reason"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    _status_command(
        ctx, project_id, identifier_id, basis_artifact_version_id, reason, json_mode, reject=True
    )


def identifier_list(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    source_id: str = typer.Option(..., "--source-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _literature(runtime).list_source_identifiers(
            _principal(runtime), _uuid(project_id, "--project-id"), _uuid(source_id, "--source-id")
        ),
    )


def _version_material(source_id: UUID, raw: str) -> SourceVersionMaterial:
    try:
        value = json.loads(raw)

        def reference(key: str):
            item = value.get(key)
            return (
                None
                if item is None
                else FrozenSourceReference(UUID(item["id"]), item["content_hash"])
            )

        publication_date = value.get("publication_date")
        return SourceVersionMaterial(
            literature_source_id=source_id,
            version_kind=SourceVersionKind(value["version_kind"]),
            predecessor_source_version=reference("predecessor_source_version"),
            correction_basis_artifact=reference("correction_basis_artifact"),
            title=value["title"],
            abstract=value.get("abstract"),
            authors=tuple(value["authors"]),
            publication_date=date.fromisoformat(publication_date) if publication_date else None,
            venue=value.get("venue"),
            external_version_label=value.get("external_version_label"),
            fulltext_artifact=reference("fulltext_artifact"),
            metadata=value.get("metadata"),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR, "invalid source version material JSON"
        ) from exc


def source_version_create(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    source_id: str = typer.Option(..., "--source-id"),
    material_json: str = typer.Option(..., "--material-json"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _source_versions(runtime).create(
            CreateSourceVersion(
                _principal(runtime),
                _uuid(project_id, "--project-id"),
                _version_material(_uuid(source_id, "--source-id"), material_json),
                _request_id(runtime),
            )
        ),
    )


def source_version_update(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    source_id: str = typer.Option(..., "--source-id"),
    source_version_id: str = typer.Option(..., "--source-version-id"),
    material_json: str = typer.Option(..., "--material-json"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _source_versions(runtime).update(
            UpdateSourceVersionDraft(
                _principal(runtime),
                _uuid(project_id, "--project-id"),
                _uuid(source_version_id, "--source-version-id"),
                _version_material(_uuid(source_id, "--source-id"), material_json),
                _request_id(runtime),
            )
        ),
    )


def _source_version_transition(
    ctx: typer.Context, project_id: str, version_id: str, json_mode: bool, operation: str
) -> None:
    runtime = _runtime(ctx)
    command = TransitionSourceVersion(
        _principal(runtime),
        _uuid(project_id, "--project-id"),
        _uuid(version_id, "--source-version-id"),
        _request_id(runtime),
    )
    _run(runtime, json_mode, lambda: getattr(_source_versions(runtime), operation)(command))


def source_version_freeze(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    source_version_id: str = typer.Option(..., "--source-version-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    _source_version_transition(ctx, project_id, source_version_id, json_mode, "freeze")


def source_version_abandon(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    source_version_id: str = typer.Option(..., "--source-version-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    _source_version_transition(ctx, project_id, source_version_id, json_mode, "abandon")


def source_version_show(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    source_version_id: str = typer.Option(..., "--source-version-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _source_versions(runtime).get(
            _principal(runtime),
            _uuid(project_id, "--project-id"),
            _uuid(source_version_id, "--source-version-id"),
        ),
    )


def source_version_list(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    source_id: str = typer.Option(..., "--source-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _source_versions(runtime).list(
            _principal(runtime), _uuid(project_id, "--project-id"), _uuid(source_id, "--source-id")
        ),
    )


def _source_versions(runtime: CliRuntime):
    service = getattr(runtime.services, "source_versions", None)
    if service is None:
        raise ResearchBaseError(
            ErrorCode.AUTHENTICATION_REQUIRED, "source version service unavailable"
        )
    return service


def _search_plans(runtime: CliRuntime):
    service = getattr(runtime.services, "literature_search_plans", None)
    if service is None:
        raise ResearchBaseError(
            ErrorCode.AUTHENTICATION_REQUIRED, "search plan service unavailable"
        )
    return service


def _search_plan_material(plan_id: UUID, raw: str, *, refs: bool) -> LiteratureSearchPlanMaterial:
    try:
        value = json.loads(raw)
        question_refs = (
            tuple(
                FrozenResearchQuestionReference(
                    UUID(item["research_question_id"]),
                    UUID(item["version_id"]),
                    item["content_hash"],
                )
                for item in value.get("research_question_refs", [])
            )
            if refs
            else ()
        )
        time_range = value.get("time_range")
        if time_range is not None:
            time_range = {
                key: date.fromisoformat(time_range[key]) if time_range.get(key) else None
                for key in ("from", "through")
            }
        language_scope = value.get("language_scope")
        return LiteratureSearchPlanMaterial(
            plan_id=plan_id,
            research_question_refs=question_refs,
            objective=value["objective"],
            source_scope=LiteratureSourceScope(value["source_scope"]),
            inclusion_criteria=value.get("inclusion_criteria"),
            exclusion_criteria=value.get("exclusion_criteria"),
            time_range=time_range,
            language_scope=tuple(language_scope) if language_scope is not None else None,
            search_strategy=LiteratureSearchStrategy(value["search_strategy"]),
            planned_providers=tuple(value["planned_providers"]),
            stopping_rule=value.get("stopping_rule"),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR, "invalid literature search plan JSON"
        ) from exc


def search_plan_create(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    material_json: str = typer.Option(..., "--material-json"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    material = _search_plan_material(UUID(int=0), material_json, refs=True)
    _run(
        runtime,
        json_mode,
        lambda: _search_plans(runtime).create(
            CreateLiteratureSearchPlan(
                _principal(runtime),
                _uuid(project_id, "--project-id"),
                material,
                _request_id(runtime),
            )
        ),
    )


def search_plan_update(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    plan_id: str = typer.Option(..., "--plan-id"),
    version_id: str = typer.Option(..., "--version-id"),
    material_json: str = typer.Option(..., "--material-json"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    plan_uuid = _uuid(plan_id, "--plan-id")
    material = _search_plan_material(plan_uuid, material_json, refs=False)
    _run(
        runtime,
        json_mode,
        lambda: _search_plans(runtime).update(
            UpdateLiteratureSearchPlanDraft(
                _principal(runtime),
                _uuid(project_id, "--project-id"),
                plan_uuid,
                _uuid(version_id, "--version-id"),
                material,
                _request_id(runtime),
            )
        ),
    )


def _search_plan_transition(ctx, project_id, plan_id, version_id, json_mode, operation):
    runtime = _runtime(ctx)
    command = TransitionLiteratureSearchPlanVersion(
        _principal(runtime),
        _uuid(project_id, "--project-id"),
        _uuid(plan_id, "--plan-id"),
        _uuid(version_id, "--version-id"),
        _request_id(runtime),
    )
    _run(runtime, json_mode, lambda: getattr(_search_plans(runtime), operation)(command))


def search_plan_freeze(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    plan_id: str = typer.Option(..., "--plan-id"),
    version_id: str = typer.Option(..., "--version-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    _search_plan_transition(ctx, project_id, plan_id, version_id, json_mode, "freeze")


def search_plan_abandon(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    plan_id: str = typer.Option(..., "--plan-id"),
    version_id: str = typer.Option(..., "--version-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    _search_plan_transition(ctx, project_id, plan_id, version_id, json_mode, "abandon")


def search_plan_revise(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    plan_id: str = typer.Option(..., "--plan-id"),
    base_version_id: str = typer.Option(..., "--base-version-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    command = ReviseLiteratureSearchPlan(
        _principal(runtime),
        _uuid(project_id, "--project-id"),
        _uuid(plan_id, "--plan-id"),
        _uuid(base_version_id, "--base-version-id"),
        _request_id(runtime),
    )
    _run(runtime, json_mode, lambda: _search_plans(runtime).revise(command))


def search_plan_add_question(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    plan_id: str = typer.Option(..., "--plan-id"),
    version_id: str = typer.Option(..., "--version-id"),
    question_version_id: str = typer.Option(..., "--question-version-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    command = EditLiteratureSearchPlanQuestions(
        _principal(runtime),
        _uuid(project_id, "--project-id"),
        _uuid(plan_id, "--plan-id"),
        _uuid(version_id, "--version-id"),
        _uuid(question_version_id, "--question-version-id"),
        _request_id(runtime),
    )
    _run(runtime, json_mode, lambda: _search_plans(runtime).add_question(command))


def search_plan_remove_question(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    plan_id: str = typer.Option(..., "--plan-id"),
    version_id: str = typer.Option(..., "--version-id"),
    question_id: str = typer.Option(..., "--question-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    command = RemoveLiteratureSearchPlanQuestion(
        _principal(runtime),
        _uuid(project_id, "--project-id"),
        _uuid(plan_id, "--plan-id"),
        _uuid(version_id, "--version-id"),
        _uuid(question_id, "--question-id"),
        _request_id(runtime),
    )
    _run(runtime, json_mode, lambda: _search_plans(runtime).remove_question(command))


def search_plan_show(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    plan_id: str = typer.Option(..., "--plan-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _search_plans(runtime).get(
            _principal(runtime), _uuid(project_id, "--project-id"), _uuid(plan_id, "--plan-id")
        ),
    )


def search_plan_list(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _search_plans(runtime).list(_principal(runtime), _uuid(project_id, "--project-id")),
    )


def _source_merge_execution(runtime: CliRuntime):
    service = getattr(runtime.services, "source_merge_execution", None)
    if service is None:
        raise ResearchBaseError(
            ErrorCode.AUTHENTICATION_REQUIRED, "source merge execution unavailable"
        )
    return service


def register(app: typer.Typer) -> None:
    literature = command_group("Public literature source identity and identifiers.")
    source = command_group("Literature source commands.")
    search_plan = command_group("Project-scoped literature search plan authoring.")
    merge_proposal = command_group("Global source merge governance proposals.")
    identifier = command_group("Source identifier commands.")
    version = command_group("Immutable literature source version commands.")
    add_command(source, "create", "Register a public literature source.", source_create)
    add_command(version, "create", "Create a draft source version.", source_version_create)
    add_command(version, "update", "Update a draft source version.", source_version_update)
    add_command(version, "freeze", "Freeze a source version.", source_version_freeze)
    add_command(version, "abandon", "Abandon a draft source version.", source_version_abandon)
    add_command(version, "show", "Read a linked source version.", source_version_show)
    add_command(version, "list", "List linked source versions.", source_version_list)
    add_command(search_plan, "create", "Create a draft literature search plan.", search_plan_create)
    add_command(search_plan, "update", "Replace draft plan material.", search_plan_update)
    add_command(
        search_plan, "revise", "Create a draft from the current frozen plan.", search_plan_revise
    )
    add_command(
        search_plan,
        "add-question",
        "Attach a frozen ResearchQuestion version.",
        search_plan_add_question,
    )
    add_command(
        search_plan,
        "remove-question",
        "Remove a ResearchQuestion identity.",
        search_plan_remove_question,
    )
    add_command(search_plan, "freeze", "Freeze the complete search plan.", search_plan_freeze)
    add_command(search_plan, "abandon", "Abandon a draft search plan.", search_plan_abandon)
    add_command(search_plan, "show", "Read a project-scoped search plan.", search_plan_show)
    add_command(search_plan, "list", "List project-scoped search plans.", search_plan_list)
    add_command(
        merge_proposal, "create", "Propose a globally governed source merge.", source_merge_propose
    )
    add_command(
        merge_proposal, "show", "Read a project-scoped source merge proposal.", source_merge_show
    )
    add_command(
        merge_proposal,
        "approve",
        "Approve a source merge proposal as project Owner.",
        source_merge_approve,
    )
    add_command(
        merge_proposal,
        "reject",
        "Reject a source merge proposal as project Owner.",
        source_merge_reject,
    )
    add_command(merge_proposal, "revoke", "Revoke a project merge approval.", source_merge_revoke)
    add_command(
        merge_proposal,
        "supersede",
        "Replace a nonterminal source merge proposal.",
        source_merge_supersede,
    )
    add_command(
        merge_proposal, "consume", "Execute an approved source merge.", source_merge_execute
    )
    add_command(source, "show", "Read a project-linked literature source.", source_show)
    add_command(source, "resolve", "Resolve a source by a typed identifier.", source_resolve)
    add_command(identifier, "add", "Add a source identifier.", identifier_add)
    add_command(identifier, "verify", "Verify an identifier using frozen basis.", identifier_verify)
    add_command(identifier, "reject", "Reject an identifier using frozen basis.", identifier_reject)
    add_command(identifier, "list", "List linked source identifier history.", identifier_list)
    literature.add_typer(source, name="source")
    literature.add_typer(merge_proposal, name="merge-proposal")
    literature.add_typer(identifier, name="identifier")
    literature.add_typer(version, name="version")
    literature.add_typer(search_plan, name="search-plan")
    for name, operation in (
        ("record-search-coverage", record_search_coverage),
        ("read-search-coverage", read_search_coverage),
        ("record-prior-art-relation", record_prior_art_relation),
        ("read-prior-art-relation", read_prior_art_relation),
        ("record-novelty-assessment", record_novelty_assessment),
        ("read-novelty-assessment", read_novelty_assessment),
    ):
        add_command(literature, name, "Record or read exact immutable novelty material.", operation)
    app.add_typer(literature, name="literature")


def _novelty(runtime):
    service = getattr(runtime.services, "novelty", None)
    if service is None:
        raise ResearchBaseError(ErrorCode.AUTHENTICATION_REQUIRED, "novelty service unavailable")
    return service


def _novelty_record(ctx, project_id, material_json, json_mode, kind):
    runtime = _runtime(ctx)

    def operation():
        try:
            values = json.loads(material_json)
            if type(values) is not dict:
                raise ValueError("closed command object required")
            for key in tuple(values):
                if key.endswith("_ids"):
                    values[key] = tuple(_novelty_id(x) for x in values[key])
                elif key == "id" or key.endswith("_id"):
                    values[key] = _novelty_id(values[key]) if values[key] is not None else None
            if "relation" in values:
                values["relation"] = PriorArtKind(values["relation"])
            if "assessment" in values:
                values["assessment"] = NoveltyOutcome(values["assessment"])
            constructor = {
                "coverage": RecordSearchCoverageCommand,
                "prior_art": RecordPriorArtRelationCommand,
                "novelty": RecordNoveltyAssessmentCommand,
            }[kind]
            command = constructor(project_id=_novelty_id(project_id), **values)
        except (ValueError, TypeError):
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR, "invalid closed novelty command"
            ) from None
        method = {
            "coverage": "record_search_coverage",
            "prior_art": "record_prior_art_relation",
            "novelty": "record_novelty_assessment",
        }[kind]
        return getattr(_novelty(runtime), method)(_principal(runtime), command)

    invoke(runtime, json_mode, operation, internal_error_exit_code=INTERNAL_ERROR_EXIT_CODE)


def _novelty_id(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError("canonical UUID required")
    return UUID(value)


def record_search_coverage(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    material_json: str = typer.Option(..., "--material-json"),
    json_mode: bool = typer.Option(False, "--json"),
):
    _novelty_record(ctx, project_id, material_json, json_mode, "coverage")


def record_prior_art_relation(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    material_json: str = typer.Option(..., "--material-json"),
    json_mode: bool = typer.Option(False, "--json"),
):
    _novelty_record(ctx, project_id, material_json, json_mode, "prior_art")


def record_novelty_assessment(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    material_json: str = typer.Option(..., "--material-json"),
    json_mode: bool = typer.Option(False, "--json"),
):
    _novelty_record(ctx, project_id, material_json, json_mode, "novelty")


def _novelty_read(ctx, project_id, identity, json_mode, method):
    runtime = _runtime(ctx)

    def operation():
        try:
            query = ExactReadQuery(_novelty_id(project_id), _novelty_id(identity))
        except ValueError:
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "canonical UUID required") from None
        return getattr(_novelty(runtime), method)(_principal(runtime), query)

    invoke(runtime, json_mode, operation, internal_error_exit_code=INTERNAL_ERROR_EXIT_CODE)


def read_search_coverage(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    id: str = typer.Option(..., "--id"),
    json_mode: bool = typer.Option(False, "--json"),
):
    _novelty_read(ctx, project_id, id, json_mode, "read_search_coverage")


def read_prior_art_relation(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    id: str = typer.Option(..., "--id"),
    json_mode: bool = typer.Option(False, "--json"),
):
    _novelty_read(ctx, project_id, id, json_mode, "read_prior_art_relation")


def read_novelty_assessment(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    id: str = typer.Option(..., "--id"),
    json_mode: bool = typer.Option(False, "--json"),
):
    _novelty_read(ctx, project_id, id, json_mode, "read_novelty_assessment")
