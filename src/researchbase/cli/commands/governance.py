"""Audit, impact, and correction commands."""

# pyright: reportArgumentType=false, reportCallIssue=false, reportAttributeAccessIssue=false

from __future__ import annotations

import typer

from researchbase.application.governance import (
    CreateAuditFindingCommand,
    CreateCorrectionRecordCommand,
    CreateImpactAssessmentCommand,
    ProposedImpactTarget,
)
from researchbase.domain.governance import (
    AuditFindingSeverity,
    CorrectionType,
    GovernanceTargetType,
    ImpactAssessmentConclusion,
    ImpactKind,
)

from ..common import (
    enum_value,
    invoke,
    list_of_objects,
    merged_payload,
    option_json,
    option_uuid,
    required,
    text_value,
    uuid_value,
)
from ..context import CliRuntime, execution_context
from ..transport import add_command, command_group


def _runtime(ctx: typer.Context) -> CliRuntime:
    runtime = ctx.find_root().obj
    if not isinstance(runtime, CliRuntime):
        raise RuntimeError("CLI runtime is not initialized")
    return runtime


def audit_create(
    ctx: typer.Context,
    project_id: str | None = typer.Option(None, "--project-id"),
    finding_type: str | None = typer.Option(None, "--finding-type"),
    severity: str | None = typer.Option(None, "--severity"),
    title: str | None = typer.Option(None, "--title"),
    description: str | None = typer.Option(None, "--description"),
    target_type: str | None = typer.Option(None, "--target-type"),
    target_id: str | None = typer.Option(None, "--target-id"),
    json_input: str | None = typer.Option(None, "--json-input", "--payload"),
    json_file: str | None = typer.Option(None, "--json-file"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)

    def operation() -> object:
        values = merged_payload(
            json_input,
            json_file,
            runtime.request_id,
            project_id=option_uuid(project_id, "--project-id", runtime.request_id),
            finding_type=finding_type,
            severity=severity,
            title=title,
            description=description,
            target_type=target_type,
            target_id=option_uuid(target_id, "--target-id", runtime.request_id),
        )
        return runtime.services.governance.create_audit_finding(
            CreateAuditFindingCommand(
                project_id=uuid_value(values, "project_id", runtime.request_id),
                finding_type=text_value(values, "finding_type", runtime.request_id),
                severity=enum_value(values, "severity", AuditFindingSeverity, runtime.request_id),
                title=text_value(values, "title", runtime.request_id),
                description=text_value(values, "description", runtime.request_id),
                target_type=enum_value(
                    values, "target_type", GovernanceTargetType, runtime.request_id
                ),
                target_id=uuid_value(values, "target_id", runtime.request_id),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def impact_assess(
    ctx: typer.Context,
    project_id: str | None = typer.Option(None, "--project-id"),
    audit_finding_id: str | None = typer.Option(None, "--audit-finding-id"),
    assessment_payload: str | None = typer.Option(None, "--assessment-payload"),
    conclusion: str | None = typer.Option(None, "--conclusion"),
    targets: str | None = typer.Option(None, "--targets"),
    json_input: str | None = typer.Option(None, "--json-input", "--payload"),
    json_file: str | None = typer.Option(None, "--json-file"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)

    def operation() -> object:
        values = merged_payload(
            json_input,
            json_file,
            runtime.request_id,
            project_id=option_uuid(project_id, "--project-id", runtime.request_id),
            audit_finding_id=option_uuid(
                audit_finding_id, "--audit-finding-id", runtime.request_id
            ),
            assessment_payload=option_json(
                assessment_payload, "--assessment-payload", runtime.request_id
            ),
            conclusion=conclusion,
            targets=option_json(targets, "--targets", runtime.request_id),
        )
        target_commands = tuple(
            ProposedImpactTarget(
                target_type=enum_value(
                    item, "target_type", GovernanceTargetType, runtime.request_id
                ),
                target_id=uuid_value(item, "target_id", runtime.request_id),
                impact_kind=enum_value(item, "impact_kind", ImpactKind, runtime.request_id),
            )
            for item in list_of_objects(values, "targets", runtime.request_id)
        )
        return runtime.services.governance.create_impact_assessment(
            CreateImpactAssessmentCommand(
                project_id=uuid_value(values, "project_id", runtime.request_id),
                audit_finding_id=optional_uuid(values, "audit_finding_id", runtime),
                assessment_payload=required(values, "assessment_payload", runtime.request_id),
                conclusion=enum_value(
                    values,
                    "conclusion",
                    ImpactAssessmentConclusion,
                    runtime.request_id,
                ),
                targets=target_commands,
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def correction_create(
    ctx: typer.Context,
    project_id: str | None = typer.Option(None, "--project-id"),
    target_type: str | None = typer.Option(None, "--target-type"),
    target_id: str | None = typer.Option(None, "--target-id"),
    correction_type: str | None = typer.Option(None, "--correction-type"),
    corrected_assertion: str | None = typer.Option(None, "--corrected-assertion"),
    reason: str | None = typer.Option(None, "--reason"),
    json_input: str | None = typer.Option(None, "--json-input", "--payload"),
    json_file: str | None = typer.Option(None, "--json-file"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)

    def operation() -> object:
        values = merged_payload(
            json_input,
            json_file,
            runtime.request_id,
            project_id=option_uuid(project_id, "--project-id", runtime.request_id),
            target_type=target_type,
            target_id=option_uuid(target_id, "--target-id", runtime.request_id),
            correction_type=correction_type,
            corrected_assertion=option_json(
                corrected_assertion, "--corrected-assertion", runtime.request_id
            ),
            reason=reason,
        )
        return runtime.services.governance.create_correction_record(
            CreateCorrectionRecordCommand(
                project_id=uuid_value(values, "project_id", runtime.request_id),
                target_type=enum_value(
                    values, "target_type", GovernanceTargetType, runtime.request_id
                ),
                target_id=uuid_value(values, "target_id", runtime.request_id),
                correction_type=enum_value(
                    values, "correction_type", CorrectionType, runtime.request_id
                ),
                corrected_assertion=required(values, "corrected_assertion", runtime.request_id),
                reason=text_value(values, "reason", runtime.request_id),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def impact_show(
    ctx: typer.Context,
    project_id: str | None = typer.Option(None, "--project-id"),
    target_type: str | None = typer.Option(None, "--target-type"),
    target_id: str | None = typer.Option(None, "--target-id"),
    json_input: str | None = typer.Option(None, "--json-input", "--payload"),
    json_file: str | None = typer.Option(None, "--json-file"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)

    def operation() -> object:
        values = merged_payload(
            json_input,
            json_file,
            runtime.request_id,
            project_id=option_uuid(project_id, "--project-id", runtime.request_id),
            target_type=target_type,
            target_id=option_uuid(target_id, "--target-id", runtime.request_id),
        )
        return runtime.services.governance_queries.downstream_impact(
            uuid_value(values, "project_id", runtime.request_id),
            enum_value(values, "target_type", GovernanceTargetType, runtime.request_id),
            uuid_value(values, "target_id", runtime.request_id),
        )

    invoke(runtime, json_mode, operation)


def optional_uuid(values: dict[str, object], name: str, runtime: CliRuntime):
    value = values.get(name)
    if value is None:
        return None
    return uuid_value(values, name, runtime.request_id)


def register(app: typer.Typer) -> None:
    reviews = command_group("Exact novelty reviews.")
    add_command(reviews, "record", "Record an independent novelty review.", novelty_review_record)
    add_command(reviews, "show", "Show exact novelty review history.", novelty_review_show)
    app.add_typer(reviews, name="novelty-review")
    revisions = command_group("Completed novelty reassessment correspondence.")
    for name, callback in (
        ("record", novelty_revision_record),
        ("show", novelty_revision_show),
        ("link", novelty_revision_link),
        ("show-link", novelty_revision_show_link),
    ):
        add_command(revisions, name, "Exact novelty revision operation.", callback)
    app.add_typer(revisions, name="novelty-revision")
    audit = command_group("Governance audit commands.")
    add_command(audit, "create", "Create an audit finding.", audit_create)
    app.add_typer(audit, name="audit")

    impact = command_group("Downstream impact commands.")
    add_command(impact, "assess", "Create an impact assessment.", impact_assess)
    add_command(impact, "show", "Read downstream impact.", impact_show)
    app.add_typer(impact, name="impact")

    correction = command_group("Correction provenance commands.")
    add_command(
        correction,
        "create",
        "Create an immutable correction record.",
        correction_create,
    )
    app.add_typer(correction, name="correction")


def _b23_invoke(ctx, json_mode, operation):
    from dataclasses import asdict

    from .literature import _principal

    runtime = _runtime(ctx)

    def run():
        return asdict(operation(runtime, _principal(runtime)))

    invoke(runtime, json_mode, run, internal_error_exit_code=1)


def _b23_uuid(value):
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    from .literature import _novelty_id

    try:
        return _novelty_id(value)
    except (ValueError, TypeError):
        raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "canonical UUID required") from None


def novelty_review_record(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    target_id: str = typer.Option(..., "--target-id"),
    review_type: str = typer.Option(..., "--review-type"),
    recommendation: str = typer.Option(..., "--recommendation"),
    summary: str = typer.Option(..., "--summary"),
    issues: str = typer.Option("[]", "--issues"),
    request: str = typer.Option(..., "--request"),
    json_mode: bool = typer.Option(False, "--json"),
):
    def run(runtime, principal):
        import json

        from researchbase.application.internal_review import (
            NoveltyReviewCommand,
            ReviewIssueRequest,
        )
        from researchbase.foundation.errors import ErrorCode, ResearchBaseError

        try:
            rows = json.loads(issues)
            if type(rows) is not list:
                raise ValueError("ordered Issue array required")
            command = NoveltyReviewCommand(
                _b23_uuid(project_id),
                "NOVELTY_ASSESSMENT",
                _b23_uuid(target_id),
                review_type,
                recommendation,
                summary,
                tuple(ReviewIssueRequest(**i) for i in rows),
                _b23_uuid(request),
            )
        except (ValueError, TypeError):
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR, "closed ordered Issues required"
            ) from None
        return runtime.services.internal_reviews.create(
            principal,
            command.project_id,
            command.target_kind,
            command.target_id,
            command.review_type,
            command.recommendation,
            command.summary,
            command.issues,
            command.request,
        )

    _b23_invoke(ctx, json_mode, run)


def novelty_review_show(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    id: str = typer.Option(..., "--id"),
    json_mode: bool = typer.Option(False, "--json"),
):
    from researchbase.application.internal_review import NoveltyReviewReadback
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    def show(runtime, principal):
        value = runtime.services.internal_reviews.read(
            principal, _b23_uuid(project_id), _b23_uuid(id)
        )
        if type(value) is not NoveltyReviewReadback:
            raise ResearchBaseError(ErrorCode.NOT_FOUND, "novelty review not found")
        return value

    _b23_invoke(ctx, json_mode, show)


def novelty_revision_record(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    id: str = typer.Option(..., "--id"),
    review_issue_id: str = typer.Option(..., "--review-issue-id"),
    result_novelty_assessment_id: str = typer.Option(..., "--result-novelty-assessment-id"),
    supersedes_revision_action_id: str | None = typer.Option(
        None, "--supersedes-revision-action-id"
    ),
    json_mode: bool = typer.Option(False, "--json"),
):
    from researchbase.application.revision_action import RecordNoveltyRevisionCommand

    _b23_invoke(
        ctx,
        json_mode,
        lambda r, p: r.services.revision_actions.record_novelty_revision(
            p,
            RecordNoveltyRevisionCommand(
                _b23_uuid(id),
                _b23_uuid(project_id),
                _b23_uuid(review_issue_id),
                _b23_uuid(result_novelty_assessment_id),
                _b23_uuid(supersedes_revision_action_id) if supersedes_revision_action_id else None,
            ),
        ),
    )


def novelty_revision_show(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    id: str = typer.Option(..., "--id"),
    json_mode: bool = typer.Option(False, "--json"),
):
    from researchbase.application.revision_action import NoveltyRevisionReadback
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    def show(runtime, principal):
        value = runtime.services.revision_actions.read_revision_action(
            principal, _b23_uuid(project_id), _b23_uuid(id)
        )
        if type(value) is not NoveltyRevisionReadback:
            raise ResearchBaseError(ErrorCode.NOT_FOUND, "novelty revision not found")
        return value

    _b23_invoke(ctx, json_mode, show)


def novelty_revision_link(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    revision_action_id: str = typer.Option(..., "--revision-action-id"),
    internal_review_record_id: str = typer.Option(..., "--internal-review-record-id"),
    json_mode: bool = typer.Option(False, "--json"),
):
    from researchbase.application.revision_action import RecordConcernReReviewCommand

    _b23_invoke(
        ctx,
        json_mode,
        lambda r, p: r.services.revision_actions.record_concern_re_review(
            p,
            RecordConcernReReviewCommand(
                _b23_uuid(project_id),
                _b23_uuid(revision_action_id),
                _b23_uuid(internal_review_record_id),
            ),
            novelty=True,
        ),
    )


def novelty_revision_show_link(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    revision_action_id: str = typer.Option(..., "--revision-action-id"),
    internal_review_record_id: str = typer.Option(..., "--internal-review-record-id"),
    json_mode: bool = typer.Option(False, "--json"),
):
    _b23_invoke(
        ctx,
        json_mode,
        lambda r, p: r.services.revision_actions.read_novelty_re_review(
            p,
            _b23_uuid(project_id),
            _b23_uuid(revision_action_id),
            _b23_uuid(internal_review_record_id),
        ),
    )
