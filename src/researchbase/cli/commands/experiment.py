"""Run, measurement, and statistical-result commands."""

# pyright: reportArgumentType=false, reportCallIssue=false, reportAttributeAccessIssue=false

from __future__ import annotations

import typer

from researchbase.application.commands import (
    AttachRunArtifactInputCommand,
    AttachRunDatasetInputCommand,
    CreateRunCommand,
    FinishRunCommand,
    RecordMeasurementCommand,
    RecordStatisticalResultCommand,
    StartRunCommand,
    StatisticalResultInputCommand,
)
from researchbase.domain.run import ArtifactInputRole, DatasetInputRole, RunStatus

from ..common import (
    enum_value,
    float_or_none,
    int_value,
    invoke,
    list_of_objects,
    merged_payload,
    option_float,
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


def run_create(
    ctx: typer.Context,
    project_id: str | None = typer.Option(None, "--project-id"),
    experiment_spec_version_id: str | None = typer.Option(None, "--experiment-spec-version-id"),
    run_type: str | None = typer.Option(None, "--run-type"),
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
            experiment_spec_version_id=option_uuid(
                experiment_spec_version_id, "--experiment-spec-version-id", runtime.request_id
            ),
            run_type=run_type,
        )
        return runtime.services.application.create_run(
            CreateRunCommand(
                project_id=uuid_value(values, "project_id", runtime.request_id),
                experiment_spec_version_id=uuid_value(
                    values, "experiment_spec_version_id", runtime.request_id
                ),
                run_type=optional_text(values, "run_type", runtime.request_id),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def run_add_dataset(
    ctx: typer.Context,
    run_id: str | None = typer.Option(None, "--run-id"),
    dataset_snapshot_id: str | None = typer.Option(None, "--dataset-snapshot-id"),
    role: str | None = typer.Option(None, "--role"),
    ordinal: str | None = typer.Option(None, "--ordinal"),
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
            run_id=option_uuid(run_id, "--run-id", runtime.request_id),
            dataset_snapshot_id=option_uuid(
                dataset_snapshot_id, "--dataset-snapshot-id", runtime.request_id
            ),
            role=role,
            ordinal=option_int(ordinal, "--ordinal", runtime.request_id),
            expected_row_version=option_int(
                expected_row_version, "--expected-row-version", runtime.request_id
            ),
        )
        return runtime.services.application.attach_run_dataset_input(
            AttachRunDatasetInputCommand(
                run_id=uuid_value(values, "run_id", runtime.request_id),
                dataset_snapshot_id=uuid_value(values, "dataset_snapshot_id", runtime.request_id),
                role=enum_value(values, "role", DatasetInputRole, runtime.request_id),
                ordinal=int_value(values, "ordinal", runtime.request_id),
                expected_row_version=int_value(values, "expected_row_version", runtime.request_id),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def run_add_artifact(
    ctx: typer.Context,
    run_id: str | None = typer.Option(None, "--run-id"),
    artifact_version_id: str | None = typer.Option(None, "--artifact-version-id"),
    role: str | None = typer.Option(None, "--role"),
    ordinal: str | None = typer.Option(None, "--ordinal"),
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
            run_id=option_uuid(run_id, "--run-id", runtime.request_id),
            artifact_version_id=option_uuid(
                artifact_version_id, "--artifact-version-id", runtime.request_id
            ),
            role=role,
            ordinal=option_int(ordinal, "--ordinal", runtime.request_id),
            expected_row_version=option_int(
                expected_row_version, "--expected-row-version", runtime.request_id
            ),
        )
        return runtime.services.application.attach_run_artifact_input(
            AttachRunArtifactInputCommand(
                run_id=uuid_value(values, "run_id", runtime.request_id),
                artifact_version_id=uuid_value(values, "artifact_version_id", runtime.request_id),
                role=enum_value(values, "role", ArtifactInputRole, runtime.request_id),
                ordinal=int_value(values, "ordinal", runtime.request_id),
                expected_row_version=int_value(values, "expected_row_version", runtime.request_id),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def run_start(
    ctx: typer.Context,
    run_id: str | None = typer.Option(None, "--run-id"),
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
            run_id=option_uuid(run_id, "--run-id", runtime.request_id),
            expected_row_version=option_int(
                expected_row_version, "--expected-row-version", runtime.request_id
            ),
        )
        return runtime.services.application.start_run(
            StartRunCommand(
                run_id=uuid_value(values, "run_id", runtime.request_id),
                expected_row_version=int_value(values, "expected_row_version", runtime.request_id),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def run_finish(
    ctx: typer.Context,
    run_id: str | None = typer.Option(None, "--run-id"),
    outcome: str | None = typer.Option(None, "--outcome"),
    expected_row_version: str | None = typer.Option(None, "--expected-row-version"),
    exit_code: str | None = typer.Option(None, "--exit-code"),
    failure_reason: str | None = typer.Option(None, "--failure-reason"),
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
            run_id=option_uuid(run_id, "--run-id", runtime.request_id),
            outcome=outcome,
            expected_row_version=option_int(
                expected_row_version, "--expected-row-version", runtime.request_id
            ),
            exit_code=option_int(exit_code, "--exit-code", runtime.request_id),
            failure_reason=failure_reason,
        )
        return runtime.services.application.finish_run(
            FinishRunCommand(
                run_id=uuid_value(values, "run_id", runtime.request_id),
                outcome=enum_value(values, "outcome", RunStatus, runtime.request_id),
                exit_code=optional_int(values, "exit_code", runtime),
                failure_reason=optional_text(values, "failure_reason", runtime.request_id),
                expected_row_version=int_value(values, "expected_row_version", runtime.request_id),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def run_provenance(
    ctx: typer.Context,
    run_id: str | None = typer.Option(None, "--run-id"),
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
            run_id=option_uuid(run_id, "--run-id", runtime.request_id),
        )
        return runtime.services.provenance.get_run_provenance(
            uuid_value(values, "run_id", runtime.request_id)
        )

    invoke(runtime, json_mode, operation)


def measurement_create(
    ctx: typer.Context,
    run_id: str | None = typer.Option(None, "--run-id"),
    metric_definition_version_id: str | None = typer.Option(None, "--metric-definition-version-id"),
    numeric_value: str | None = typer.Option(None, "--numeric-value"),
    structured_value: str | None = typer.Option(None, "--structured-value"),
    unit: str | None = typer.Option(None, "--unit"),
    evaluation_scope: str | None = typer.Option(None, "--evaluation-scope"),
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
            run_id=option_uuid(run_id, "--run-id", runtime.request_id),
            metric_definition_version_id=option_uuid(
                metric_definition_version_id,
                "--metric-definition-version-id",
                runtime.request_id,
            ),
            numeric_value=option_float(numeric_value, "--numeric-value", runtime.request_id),
            structured_value=option_json(
                structured_value, "--structured-value", runtime.request_id
            ),
            unit=unit,
            evaluation_scope=option_json(
                evaluation_scope, "--evaluation-scope", runtime.request_id
            ),
        )
        return runtime.services.application.record_measurement(
            RecordMeasurementCommand(
                run_id=uuid_value(values, "run_id", runtime.request_id),
                metric_definition_version_id=uuid_value(
                    values, "metric_definition_version_id", runtime.request_id
                ),
                numeric_value=float_or_none(values, "numeric_value", runtime.request_id),
                structured_value=values.get("structured_value"),
                unit=optional_text(values, "unit", runtime.request_id),
                evaluation_scope=values.get("evaluation_scope"),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def stats_create(
    ctx: typer.Context,
    project_id: str | None = typer.Option(None, "--project-id"),
    analysis_type: str | None = typer.Option(None, "--analysis-type"),
    result_payload: str | None = typer.Option(None, "--result-payload"),
    analysis_definition: str | None = typer.Option(None, "--analysis-definition"),
    inputs: str | None = typer.Option(None, "--inputs"),
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
            analysis_type=analysis_type,
            result_payload=option_json(result_payload, "--result-payload", runtime.request_id),
            analysis_definition=option_json(
                analysis_definition, "--analysis-definition", runtime.request_id
            ),
            inputs=option_json(inputs, "--inputs", runtime.request_id),
        )
        input_commands = tuple(
            StatisticalResultInputCommand(
                measurement_id=uuid_value(item, "measurement_id", runtime.request_id),
                input_role=optional_text(item, "input_role", runtime.request_id) or "input",
                ordinal=optional_nonnegative_int(item, "ordinal", runtime),
            )
            for item in list_of_objects(values, "inputs", runtime.request_id)
        )
        return runtime.services.application.record_statistical_result(
            RecordStatisticalResultCommand(
                project_id=uuid_value(values, "project_id", runtime.request_id),
                analysis_type=text_value(values, "analysis_type", runtime.request_id),
                result_payload=required(values, "result_payload", runtime.request_id),
                analysis_definition=required(values, "analysis_definition", runtime.request_id),
                inputs=input_commands,
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def optional_int(values: dict[str, object], name: str, runtime: CliRuntime) -> int | None:
    value = values.get(name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise CliTransportError(
            f"{name} must be an integer",
            request_id=runtime.request_id,
            details={"field": name},
        )
    return value


def optional_nonnegative_int(values: dict[str, object], name: str, runtime: CliRuntime) -> int:
    value = optional_int(values, name, runtime)
    if value is None:
        return 0
    if value < 0:
        raise CliTransportError(
            f"{name} must be non-negative",
            request_id=runtime.request_id,
            details={"field": name},
        )
    return value


def register(app: typer.Typer) -> None:
    run = command_group("Run and provenance commands.")
    add_command(run, "create", "Create a planned run.", run_create)
    add_command(run, "add-dataset", "Attach a dataset snapshot to a run.", run_add_dataset)
    add_command(run, "add-artifact", "Attach an artifact version to a run.", run_add_artifact)
    add_command(run, "start", "Start and seal a run.", run_start)
    add_command(run, "finish", "Finish a run.", run_finish)
    add_command(run, "provenance", "Read exact run provenance.", run_provenance)
    app.add_typer(run, name="run")

    measurement = command_group("Measurement commands.")
    add_command(measurement, "create", "Record an immutable measurement.", measurement_create)
    app.add_typer(measurement, name="measurement")

    stats = command_group("Statistical-result commands.")
    add_command(stats, "create", "Record an immutable statistical result.", stats_create)
    app.add_typer(stats, name="stats")
