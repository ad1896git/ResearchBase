"""Project, research-question, hypothesis, and experiment-spec commands."""

# pyright: reportArgumentType=false, reportCallIssue=false, reportAttributeAccessIssue=false

from __future__ import annotations

from uuid import UUID

import typer

from researchbase.application.commands import (
    CreateExperimentSpecCommand,
    CreateHypothesisCommand,
    CreateProjectCommand,
    CreateResearchQuestionCommand,
    FreezeExperimentSpecCommand,
    FreezeHypothesisCommand,
    FreezeResearchQuestionCommand,
    ReviseExperimentSpecCommand,
    ReviseHypothesisCommand,
    ReviseResearchQuestionCommand,
    WriteProjectionTarget,
)

from ..common import (
    application_write,
    invoke,
    merged_payload,
    option_int,
    option_json,
    option_uuid,
    optional_text,
    required,
    text_value,
    uuid_value,
)
from ..context import CliRuntime, execution_context
from ..errors import CliTransportError
from ..transport import add_command, command_group


def _runtime(ctx: typer.Context) -> CliRuntime:
    runtime = ctx.find_root().obj
    if not isinstance(runtime, CliRuntime):
        raise RuntimeError("CLI runtime is not initialized")
    return runtime


def project_create(
    ctx: typer.Context,
    name: str | None = typer.Option(None, "--name"),
    description: str | None = typer.Option(None, "--description"),
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
            name=name,
            description=description,
        )
        return application_write(
            runtime.services.application,
            WriteProjectionTarget.PROJECT,
            lambda: runtime.services.application.create_project(
                CreateProjectCommand(
                    text_value(values, "name", runtime.request_id),
                    optional_text(values, "description", runtime.request_id),
                    execution_context(runtime),
                )
            ),
        )

    invoke(runtime, json_mode, operation)


def rq_create(
    ctx: typer.Context,
    project_id: str | None = typer.Option(None, "--project-id"),
    question_text: str | None = typer.Option(None, "--question-text"),
    scope: str | None = typer.Option(None, "--scope"),
    rationale: str | None = typer.Option(None, "--rationale"),
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
            question_text=question_text,
            scope=option_json(scope, "--scope", runtime.request_id),
            rationale=rationale,
        )
        return application_write(
            runtime.services.application,
            WriteProjectionTarget.RESEARCH_QUESTION,
            lambda: runtime.services.application.create_research_question(
                CreateResearchQuestionCommand(
                    project_id=uuid_value(values, "project_id", runtime.request_id),
                    question_text=text_value(values, "question_text", runtime.request_id),
                    scope=values.get("scope"),
                    rationale=optional_text(values, "rationale", runtime.request_id),
                    context=execution_context(runtime),
                )
            ),
        )

    invoke(runtime, json_mode, operation)


def rq_revise(
    ctx: typer.Context,
    research_question_id: str | None = typer.Option(None, "--research-question-id"),
    question_text: str | None = typer.Option(None, "--question-text"),
    scope: str | None = typer.Option(None, "--scope"),
    rationale: str | None = typer.Option(None, "--rationale"),
    expected_row_version: str | None = typer.Option(None, "--expected-row-version"),
    base_version_id: str | None = typer.Option(None, "--base-version-id"),
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
            research_question_id=option_uuid(
                research_question_id, "--research-question-id", runtime.request_id
            ),
            question_text=question_text,
            scope=option_json(scope, "--scope", runtime.request_id),
            rationale=rationale,
            expected_row_version=option_int(
                expected_row_version, "--expected-row-version", runtime.request_id
            ),
            base_version_id=option_uuid(base_version_id, "--base-version-id", runtime.request_id),
        )
        return application_write(
            runtime.services.application,
            WriteProjectionTarget.RESEARCH_QUESTION,
            lambda: runtime.services.application.revise_research_question(
                ReviseResearchQuestionCommand(
                    research_question_id=uuid_value(
                        values, "research_question_id", runtime.request_id
                    ),
                    question_text=text_value(values, "question_text", runtime.request_id),
                    scope=values.get("scope"),
                    rationale=optional_text(values, "rationale", runtime.request_id),
                    expected_row_version=int_value_from_values(
                        values, "expected_row_version", runtime
                    ),
                    base_version_id=optional_uuid_from_values(values, "base_version_id", runtime),
                    context=execution_context(runtime),
                )
            ),
        )

    invoke(runtime, json_mode, operation)


def rq_freeze(
    ctx: typer.Context,
    research_question_id: str | None = typer.Option(None, "--research-question-id"),
    version_id: str | None = typer.Option(None, "--version-id"),
    expected_row_version: str | None = typer.Option(None, "--expected-row-version"),
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
            research_question_id=option_uuid(
                research_question_id, "--research-question-id", runtime.request_id
            ),
            version_id=option_uuid(version_id, "--version-id", runtime.request_id),
            expected_row_version=option_int(
                expected_row_version, "--expected-row-version", runtime.request_id
            ),
        )
        return application_write(
            runtime.services.application,
            WriteProjectionTarget.RESEARCH_QUESTION_VERSION,
            lambda: runtime.services.application.freeze_research_question(
                FreezeResearchQuestionCommand(
                    research_question_id=uuid_value(
                        values, "research_question_id", runtime.request_id
                    ),
                    version_id=uuid_value(values, "version_id", runtime.request_id),
                    expected_row_version=optional_int_from_values(
                        values, "expected_row_version", runtime
                    ),
                    context=execution_context(runtime),
                )
            ),
        )

    invoke(runtime, json_mode, operation)


def hypothesis_create(
    ctx: typer.Context,
    project_id: str | None = typer.Option(None, "--project-id"),
    statement: str | None = typer.Option(None, "--statement"),
    expected_direction: str | None = typer.Option(None, "--expected-direction"),
    success_criteria: str | None = typer.Option(None, "--success-criteria"),
    rationale: str | None = typer.Option(None, "--rationale"),
    research_question_id: str | None = typer.Option(None, "--research-question-id"),
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
            statement=statement,
            expected_direction=expected_direction,
            success_criteria=option_json(
                success_criteria, "--success-criteria", runtime.request_id
            ),
            rationale=rationale,
            research_question_id=option_uuid(
                research_question_id, "--research-question-id", runtime.request_id
            ),
        )
        return application_write(
            runtime.services.application,
            WriteProjectionTarget.HYPOTHESIS,
            lambda: runtime.services.application.create_hypothesis(
                CreateHypothesisCommand(
                    project_id=uuid_value(values, "project_id", runtime.request_id),
                    statement=text_value(values, "statement", runtime.request_id),
                    expected_direction=optional_text(
                        values, "expected_direction", runtime.request_id
                    ),
                    success_criteria=values.get("success_criteria"),
                    rationale=optional_text(values, "rationale", runtime.request_id),
                    research_question_id=optional_uuid_from_values(
                        values, "research_question_id", runtime
                    ),
                    context=execution_context(runtime),
                )
            ),
        )

    invoke(runtime, json_mode, operation)


def hypothesis_revise(
    ctx: typer.Context,
    hypothesis_id: str | None = typer.Option(None, "--hypothesis-id"),
    statement: str | None = typer.Option(None, "--statement"),
    expected_direction: str | None = typer.Option(None, "--expected-direction"),
    success_criteria: str | None = typer.Option(None, "--success-criteria"),
    rationale: str | None = typer.Option(None, "--rationale"),
    expected_row_version: str | None = typer.Option(None, "--expected-row-version"),
    base_version_id: str | None = typer.Option(None, "--base-version-id"),
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
            hypothesis_id=option_uuid(hypothesis_id, "--hypothesis-id", runtime.request_id),
            statement=statement,
            expected_direction=expected_direction,
            success_criteria=option_json(
                success_criteria, "--success-criteria", runtime.request_id
            ),
            rationale=rationale,
            expected_row_version=option_int(
                expected_row_version, "--expected-row-version", runtime.request_id
            ),
            base_version_id=option_uuid(base_version_id, "--base-version-id", runtime.request_id),
        )
        return application_write(
            runtime.services.application,
            WriteProjectionTarget.HYPOTHESIS,
            lambda: runtime.services.application.revise_hypothesis(
                ReviseHypothesisCommand(
                    hypothesis_id=uuid_value(values, "hypothesis_id", runtime.request_id),
                    statement=text_value(values, "statement", runtime.request_id),
                    expected_direction=optional_text(
                        values, "expected_direction", runtime.request_id
                    ),
                    success_criteria=values.get("success_criteria"),
                    rationale=optional_text(values, "rationale", runtime.request_id),
                    expected_row_version=int_value_from_values(
                        values, "expected_row_version", runtime
                    ),
                    base_version_id=optional_uuid_from_values(values, "base_version_id", runtime),
                    context=execution_context(runtime),
                )
            ),
        )

    invoke(runtime, json_mode, operation)


def hypothesis_freeze(
    ctx: typer.Context,
    hypothesis_id: str | None = typer.Option(None, "--hypothesis-id"),
    version_id: str | None = typer.Option(None, "--version-id"),
    expected_row_version: str | None = typer.Option(None, "--expected-row-version"),
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
            hypothesis_id=option_uuid(hypothesis_id, "--hypothesis-id", runtime.request_id),
            version_id=option_uuid(version_id, "--version-id", runtime.request_id),
            expected_row_version=option_int(
                expected_row_version, "--expected-row-version", runtime.request_id
            ),
        )
        return application_write(
            runtime.services.application,
            WriteProjectionTarget.HYPOTHESIS_VERSION,
            lambda: runtime.services.application.freeze_hypothesis(
                FreezeHypothesisCommand(
                    hypothesis_id=uuid_value(values, "hypothesis_id", runtime.request_id),
                    version_id=uuid_value(values, "version_id", runtime.request_id),
                    expected_row_version=optional_int_from_values(
                        values, "expected_row_version", runtime
                    ),
                    context=execution_context(runtime),
                )
            ),
        )

    invoke(runtime, json_mode, operation)


def spec_create(
    ctx: typer.Context,
    project_id: str | None = typer.Option(None, "--project-id"),
    hypothesis_id: str | None = typer.Option(None, "--hypothesis-id"),
    title: str | None = typer.Option(None, "--title"),
    objective: str | None = typer.Option(None, "--objective"),
    protocol: str | None = typer.Option(None, "--protocol"),
    planned_metrics: str | None = typer.Option(None, "--planned-metrics"),
    seed_policy: str | None = typer.Option(None, "--seed-policy"),
    analysis_plan: str | None = typer.Option(None, "--analysis-plan"),
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
            hypothesis_id=option_uuid(hypothesis_id, "--hypothesis-id", runtime.request_id),
            title=title,
            objective=objective,
            protocol=option_json(protocol, "--protocol", runtime.request_id),
            planned_metrics=option_json(planned_metrics, "--planned-metrics", runtime.request_id),
            seed_policy=option_json(seed_policy, "--seed-policy", runtime.request_id),
            analysis_plan=option_json(analysis_plan, "--analysis-plan", runtime.request_id),
        )
        return application_write(
            runtime.services.application,
            WriteProjectionTarget.EXPERIMENT_SPEC,
            lambda: runtime.services.application.create_experiment_spec(
                CreateExperimentSpecCommand(
                    project_id=uuid_value(values, "project_id", runtime.request_id),
                    hypothesis_id=optional_uuid_from_values(values, "hypothesis_id", runtime),
                    title=text_value(values, "title", runtime.request_id),
                    objective=text_value(values, "objective", runtime.request_id),
                    protocol=required(values, "protocol", runtime.request_id),
                    planned_metrics=values.get("planned_metrics"),
                    seed_policy=values.get("seed_policy"),
                    analysis_plan=values.get("analysis_plan"),
                    context=execution_context(runtime),
                )
            ),
        )

    invoke(runtime, json_mode, operation)


def spec_revise(
    ctx: typer.Context,
    experiment_spec_id: str | None = typer.Option(None, "--experiment-spec-id"),
    title: str | None = typer.Option(None, "--title"),
    objective: str | None = typer.Option(None, "--objective"),
    protocol: str | None = typer.Option(None, "--protocol"),
    planned_metrics: str | None = typer.Option(None, "--planned-metrics"),
    seed_policy: str | None = typer.Option(None, "--seed-policy"),
    analysis_plan: str | None = typer.Option(None, "--analysis-plan"),
    expected_row_version: str | None = typer.Option(None, "--expected-row-version"),
    base_version_id: str | None = typer.Option(None, "--base-version-id"),
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
            experiment_spec_id=option_uuid(
                experiment_spec_id, "--experiment-spec-id", runtime.request_id
            ),
            title=title,
            objective=objective,
            protocol=option_json(protocol, "--protocol", runtime.request_id),
            planned_metrics=option_json(planned_metrics, "--planned-metrics", runtime.request_id),
            seed_policy=option_json(seed_policy, "--seed-policy", runtime.request_id),
            analysis_plan=option_json(analysis_plan, "--analysis-plan", runtime.request_id),
            expected_row_version=option_int(
                expected_row_version, "--expected-row-version", runtime.request_id
            ),
            base_version_id=option_uuid(base_version_id, "--base-version-id", runtime.request_id),
        )
        return application_write(
            runtime.services.application,
            WriteProjectionTarget.EXPERIMENT_SPEC,
            lambda: runtime.services.application.revise_experiment_spec(
                ReviseExperimentSpecCommand(
                    experiment_spec_id=uuid_value(values, "experiment_spec_id", runtime.request_id),
                    title=text_value(values, "title", runtime.request_id),
                    objective=text_value(values, "objective", runtime.request_id),
                    protocol=required(values, "protocol", runtime.request_id),
                    planned_metrics=values.get("planned_metrics"),
                    seed_policy=values.get("seed_policy"),
                    analysis_plan=values.get("analysis_plan"),
                    expected_row_version=int_value_from_values(
                        values, "expected_row_version", runtime
                    ),
                    base_version_id=optional_uuid_from_values(values, "base_version_id", runtime),
                    context=execution_context(runtime),
                )
            ),
        )

    invoke(runtime, json_mode, operation)


def spec_freeze(
    ctx: typer.Context,
    experiment_spec_id: str | None = typer.Option(None, "--experiment-spec-id"),
    version_id: str | None = typer.Option(None, "--version-id"),
    expected_row_version: str | None = typer.Option(None, "--expected-row-version"),
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
            experiment_spec_id=option_uuid(
                experiment_spec_id, "--experiment-spec-id", runtime.request_id
            ),
            version_id=option_uuid(version_id, "--version-id", runtime.request_id),
            expected_row_version=option_int(
                expected_row_version, "--expected-row-version", runtime.request_id
            ),
        )
        return application_write(
            runtime.services.application,
            WriteProjectionTarget.EXPERIMENT_SPEC_VERSION,
            lambda: runtime.services.application.freeze_experiment_spec(
                FreezeExperimentSpecCommand(
                    experiment_spec_id=uuid_value(values, "experiment_spec_id", runtime.request_id),
                    version_id=uuid_value(values, "version_id", runtime.request_id),
                    expected_row_version=optional_int_from_values(
                        values, "expected_row_version", runtime
                    ),
                    context=execution_context(runtime),
                )
            ),
        )

    invoke(runtime, json_mode, operation)


def int_value_from_values(values: dict[str, object], name: str, runtime: CliRuntime) -> int:
    value = values.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise CliTransportError(
            f"{name} must be an integer", request_id=runtime.request_id, details={"field": name}
        )
    if value < 1:
        raise CliTransportError(
            f"{name} must be at least 1", request_id=runtime.request_id, details={"field": name}
        )
    return value


def optional_int_from_values(
    values: dict[str, object], name: str, runtime: CliRuntime
) -> int | None:
    value = values.get(name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise CliTransportError(
            f"{name} must be a positive integer",
            request_id=runtime.request_id,
            details={"field": name},
        )
    return value


def optional_uuid_from_values(
    values: dict[str, object], name: str, runtime: CliRuntime
) -> object | None:
    value = values.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise CliTransportError(
            f"{name} must be a valid UUID", request_id=runtime.request_id, details={"field": name}
        )
    try:
        return UUID(value)
    except ValueError as exc:
        raise CliTransportError(
            f"{name} must be a valid UUID", request_id=runtime.request_id, details={"field": name}
        ) from exc


def register(app: typer.Typer) -> None:
    project = command_group("Project commands.")
    add_command(project, "create", "Create a project.", project_create)
    app.add_typer(project, name="project")

    rq = command_group("Research question commands.")
    add_command(rq, "create", "Create a research question.", rq_create)
    add_command(rq, "revise", "Create a new research-question version.", rq_revise)
    add_command(rq, "freeze", "Freeze a research-question version.", rq_freeze)
    app.add_typer(rq, name="rq")

    hypothesis = command_group("Hypothesis commands.")
    add_command(hypothesis, "create", "Create a hypothesis.", hypothesis_create)
    add_command(hypothesis, "revise", "Create a new hypothesis version.", hypothesis_revise)
    add_command(hypothesis, "freeze", "Freeze a hypothesis version.", hypothesis_freeze)
    app.add_typer(hypothesis, name="hypothesis")

    spec = command_group("Experiment specification commands.")
    add_command(spec, "create", "Create an experiment specification.", spec_create)
    add_command(spec, "revise", "Create a new experiment-spec version.", spec_revise)
    add_command(spec, "freeze", "Freeze an experiment-spec version.", spec_freeze)
    app.add_typer(spec, name="spec")
