"""Dataset, Artifact, and Metric Definition command groups."""

# pyright: reportArgumentType=false, reportCallIssue=false, reportAttributeAccessIssue=false

from __future__ import annotations

from pathlib import Path

import typer

from researchbase.application.commands import (
    CreateArtifactCommand,
    CreateArtifactVersionCommand,
    CreateDatasetSnapshotCommand,
    CreateMetricDefinitionCommand,
    FreezeArtifactVersionCommand,
    FreezeMetricDefinitionCommand,
    RegisterDatasetCommand,
    ReviseMetricDefinitionCommand,
)

from ..common import (
    invoke,
    merged_payload,
    option_base64,
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


def dataset_create(
    ctx: typer.Context,
    name: str | None = typer.Option(None, "--name"),
    project_id: str | None = typer.Option(None, "--project-id"),
    description: str | None = typer.Option(None, "--description"),
    source_locator: str | None = typer.Option(None, "--source-locator"),
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
            project_id=option_uuid(project_id, "--project-id", runtime.request_id),
            description=description,
            source_locator=source_locator,
        )
        return runtime.services.application.register_dataset(
            RegisterDatasetCommand(
                project_id=optional_uuid(values, "project_id", runtime),
                name=text_value(values, "name", runtime.request_id),
                description=optional_text(values, "description", runtime.request_id),
                source_locator=optional_text(values, "source_locator", runtime.request_id),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def dataset_snapshot(
    ctx: typer.Context,
    dataset_id: str | None = typer.Option(None, "--dataset-id"),
    manifest_hash: str | None = typer.Option(None, "--manifest-hash"),
    selection_definition: str | None = typer.Option(None, "--selection-definition"),
    manifest_locator: str | None = typer.Option(None, "--manifest-locator"),
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
            dataset_id=option_uuid(dataset_id, "--dataset-id", runtime.request_id),
            manifest_hash=manifest_hash,
            selection_definition=option_json(
                selection_definition, "--selection-definition", runtime.request_id
            ),
            manifest_locator=manifest_locator,
        )
        return runtime.services.application.create_dataset_snapshot(
            CreateDatasetSnapshotCommand(
                dataset_id=uuid_value(values, "dataset_id", runtime.request_id),
                manifest_hash=text_value(values, "manifest_hash", runtime.request_id),
                selection_definition=required(values, "selection_definition", runtime.request_id),
                manifest_locator=optional_text(values, "manifest_locator", runtime.request_id),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def artifact_create(
    ctx: typer.Context,
    artifact_type: str | None = typer.Option(None, "--artifact-type"),
    name: str | None = typer.Option(None, "--name"),
    project_id: str | None = typer.Option(None, "--project-id"),
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
            artifact_type=artifact_type,
            name=name,
            project_id=option_uuid(project_id, "--project-id", runtime.request_id),
            description=description,
        )
        return runtime.services.application.create_artifact(
            CreateArtifactCommand(
                project_id=optional_uuid(values, "project_id", runtime),
                artifact_type=text_value(values, "artifact_type", runtime.request_id),
                name=text_value(values, "name", runtime.request_id),
                description=optional_text(values, "description", runtime.request_id),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def artifact_revise(
    ctx: typer.Context,
    artifact_id: str | None = typer.Option(None, "--artifact-id"),
    data_base64: str | None = typer.Option(None, "--data-base64"),
    data_file: str | None = typer.Option(None, "--data-file"),
    content_hash: str | None = typer.Option(None, "--content-hash"),
    locator: str | None = typer.Option(None, "--locator"),
    media_type: str | None = typer.Option(None, "--media-type"),
    byte_size: str | None = typer.Option(None, "--byte-size"),
    metadata: str | None = typer.Option(None, "--metadata"),
    json_input: str | None = typer.Option(None, "--json-input", "--payload"),
    json_file: str | None = typer.Option(None, "--json-file"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)

    def operation() -> object:
        if data_file is not None and data_base64 is not None:
            raise CliTransportError(
                "use only one of --data-file and --data-base64",
                request_id=runtime.request_id,
                details={"options": ["--data-file", "--data-base64"]},
            )
        file_data = None
        if data_file is not None:
            try:
                file_data = Path(data_file).read_bytes()
            except OSError as exc:
                raise CliTransportError(
                    "--data-file could not be read",
                    request_id=runtime.request_id,
                    details={"option": "--data-file"},
                ) from exc
        values = merged_payload(
            json_input,
            json_file,
            runtime.request_id,
            artifact_id=option_uuid(artifact_id, "--artifact-id", runtime.request_id),
            data=file_data
            if file_data is not None
            else option_base64(data_base64, "--data-base64", runtime.request_id),
            content_hash=content_hash,
            locator=locator,
            media_type=media_type,
            byte_size=option_int(byte_size, "--byte-size", runtime.request_id),
            metadata=option_json(metadata, "--metadata", runtime.request_id),
        )
        payload_data = values.get("data_base64")
        if payload_data is not None:
            if file_data is not None or data_base64 is not None:
                raise CliTransportError(
                    "use only one of data_base64 and --data-base64/--data-file",
                    request_id=runtime.request_id,
                    details={"field": "data_base64"},
                )
            if not isinstance(payload_data, str):
                raise CliTransportError(
                    "data_base64 must be a base64 string",
                    request_id=runtime.request_id,
                    details={"field": "data_base64"},
                )
            values["data"] = option_base64(payload_data, "data_base64", runtime.request_id)
        return runtime.services.application.create_artifact_version(
            CreateArtifactVersionCommand(
                artifact_id=uuid_value(values, "artifact_id", runtime.request_id),
                data=bytes_value(values.get("data"), runtime),
                content_hash=optional_text(values, "content_hash", runtime.request_id),
                locator=optional_text(values, "locator", runtime.request_id),
                media_type=optional_text(values, "media_type", runtime.request_id),
                byte_size=optional_nonnegative_int(values, "byte_size", runtime),
                metadata=values.get("metadata"),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def artifact_freeze(
    ctx: typer.Context,
    artifact_id: str | None = typer.Option(None, "--artifact-id"),
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
            artifact_id=option_uuid(artifact_id, "--artifact-id", runtime.request_id),
            version_id=option_uuid(version_id, "--version-id", runtime.request_id),
            expected_row_version=option_int(
                expected_row_version, "--expected-row-version", runtime.request_id
            ),
        )
        return runtime.services.application.freeze_artifact_version(
            FreezeArtifactVersionCommand(
                artifact_id=uuid_value(values, "artifact_id", runtime.request_id),
                version_id=uuid_value(values, "version_id", runtime.request_id),
                expected_row_version=optional_int(values, "expected_row_version", runtime),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def metric_create(
    ctx: typer.Context,
    name: str | None = typer.Option(None, "--name"),
    definition: str | None = typer.Option(None, "--definition"),
    project_id: str | None = typer.Option(None, "--project-id"),
    unit: str | None = typer.Option(None, "--unit"),
    aggregation: str | None = typer.Option(None, "--aggregation"),
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
            definition=option_json(definition, "--definition", runtime.request_id),
            project_id=option_uuid(project_id, "--project-id", runtime.request_id),
            unit=unit,
            aggregation=aggregation,
        )
        return runtime.services.application.create_metric_definition(
            CreateMetricDefinitionCommand(
                project_id=optional_uuid(values, "project_id", runtime),
                name=text_value(values, "name", runtime.request_id),
                definition=required(values, "definition", runtime.request_id),
                unit=optional_text(values, "unit", runtime.request_id),
                aggregation=optional_text(values, "aggregation", runtime.request_id),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def metric_revise(
    ctx: typer.Context,
    metric_definition_id: str | None = typer.Option(None, "--metric-definition-id"),
    definition: str | None = typer.Option(None, "--definition"),
    unit: str | None = typer.Option(None, "--unit"),
    aggregation: str | None = typer.Option(None, "--aggregation"),
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
            metric_definition_id=option_uuid(
                metric_definition_id, "--metric-definition-id", runtime.request_id
            ),
            definition=option_json(definition, "--definition", runtime.request_id),
            unit=unit,
            aggregation=aggregation,
            expected_row_version=option_int(
                expected_row_version, "--expected-row-version", runtime.request_id
            ),
        )
        return runtime.services.application.revise_metric_definition(
            ReviseMetricDefinitionCommand(
                metric_definition_id=uuid_value(values, "metric_definition_id", runtime.request_id),
                definition=required(values, "definition", runtime.request_id),
                unit=optional_text(values, "unit", runtime.request_id),
                aggregation=optional_text(values, "aggregation", runtime.request_id),
                expected_row_version=int_value(values, "expected_row_version", runtime),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def metric_freeze(
    ctx: typer.Context,
    metric_definition_id: str | None = typer.Option(None, "--metric-definition-id"),
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
            metric_definition_id=option_uuid(
                metric_definition_id, "--metric-definition-id", runtime.request_id
            ),
            version_id=option_uuid(version_id, "--version-id", runtime.request_id),
            expected_row_version=option_int(
                expected_row_version, "--expected-row-version", runtime.request_id
            ),
        )
        return runtime.services.application.freeze_metric_definition(
            FreezeMetricDefinitionCommand(
                metric_definition_id=uuid_value(values, "metric_definition_id", runtime.request_id),
                version_id=uuid_value(values, "version_id", runtime.request_id),
                expected_row_version=optional_int(values, "expected_row_version", runtime),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def optional_uuid(values: dict[str, object], name: str, runtime: CliRuntime):
    value = values.get(name)
    if value is None:
        return None
    return uuid_value(values, name, runtime.request_id)


def optional_int(values: dict[str, object], name: str, runtime: CliRuntime) -> int | None:
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


def optional_nonnegative_int(
    values: dict[str, object], name: str, runtime: CliRuntime
) -> int | None:
    value = values.get(name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CliTransportError(
            f"{name} must be a non-negative integer",
            request_id=runtime.request_id,
            details={"field": name},
        )
    return value


def bytes_value(value: object, runtime: CliRuntime) -> bytes | None:
    if value is None:
        return None
    if not isinstance(value, bytes):
        raise CliTransportError(
            "data must be supplied as base64 or a file",
            request_id=runtime.request_id,
            details={"field": "data"},
        )
    return value


def int_value(values: dict[str, object], name: str, runtime: CliRuntime) -> int:
    value = optional_int(values, name, runtime)
    if value is None:
        raise CliTransportError(
            f"{name} is required",
            request_id=runtime.request_id,
            details={"field": name},
        )
    return value


def register(app: typer.Typer) -> None:
    dataset = command_group("Dataset commands.")
    add_command(dataset, "create", "Register a dataset.", dataset_create)
    add_command(dataset, "snapshot", "Create an immutable dataset snapshot.", dataset_snapshot)
    app.add_typer(dataset, name="dataset")

    artifact = command_group("Artifact commands.")
    add_command(artifact, "create", "Register an artifact.", artifact_create)
    add_command(artifact, "revise", "Create an artifact version.", artifact_revise)
    add_command(artifact, "freeze", "Freeze an artifact version.", artifact_freeze)
    app.add_typer(artifact, name="artifact")

    metric = command_group("Metric definition commands.")
    add_command(metric, "create", "Create a metric definition.", metric_create)
    add_command(metric, "revise", "Create a metric-definition version.", metric_revise)
    add_command(metric, "freeze", "Freeze a metric-definition version.", metric_freeze)
    app.add_typer(metric, name="metric")
