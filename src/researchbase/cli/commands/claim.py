"""Claim, evidence, and historical claim-trace commands."""

# pyright: reportArgumentType=false, reportCallIssue=false, reportAttributeAccessIssue=false

from __future__ import annotations

import typer

from researchbase.application.commands import (
    CreateClaimCommand,
    FreezeClaimVersionCommand,
    LinkEvidenceCommand,
    ReviseClaimCommand,
)
from researchbase.domain.claim import EvidenceRelationType

from ..commands.research import optional_uuid_from_values
from ..common import (
    enum_value,
    int_value,
    invoke,
    merged_payload,
    option_int,
    option_json,
    option_uuid,
    optional_text,
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


def claim_create(
    ctx: typer.Context,
    project_id: str | None = typer.Option(None, "--project-id"),
    statement: str | None = typer.Option(None, "--statement"),
    scope: str | None = typer.Option(None, "--scope"),
    qualification: str | None = typer.Option(None, "--qualification"),
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
            scope=option_json(scope, "--scope", runtime.request_id),
            qualification=qualification,
        )
        return runtime.services.application.create_claim(
            CreateClaimCommand(
                project_id=uuid_value(values, "project_id", runtime.request_id),
                statement=text_value(values, "statement", runtime.request_id),
                scope=values.get("scope"),
                qualification=optional_text(values, "qualification", runtime.request_id),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def claim_revise(
    ctx: typer.Context,
    claim_id: str | None = typer.Option(None, "--claim-id"),
    statement: str | None = typer.Option(None, "--statement"),
    scope: str | None = typer.Option(None, "--scope"),
    qualification: str | None = typer.Option(None, "--qualification"),
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
            claim_id=option_uuid(claim_id, "--claim-id", runtime.request_id),
            statement=statement,
            scope=option_json(scope, "--scope", runtime.request_id),
            qualification=qualification,
            expected_row_version=option_int(
                expected_row_version, "--expected-row-version", runtime.request_id
            ),
            base_version_id=option_uuid(base_version_id, "--base-version-id", runtime.request_id),
        )
        return runtime.services.application.revise_claim(
            ReviseClaimCommand(
                claim_id=uuid_value(values, "claim_id", runtime.request_id),
                statement=optional_text(values, "statement", runtime.request_id),
                scope=values.get("scope"),
                qualification=optional_text(values, "qualification", runtime.request_id),
                expected_row_version=int_value(values, "expected_row_version", runtime.request_id),
                base_version_id=optional_uuid_from_values(values, "base_version_id", runtime),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def claim_add_evidence(
    ctx: typer.Context,
    claim_id: str | None = typer.Option(None, "--claim-id"),
    claim_version_id: str | None = typer.Option(None, "--claim-version-id"),
    measurement_id: str | None = typer.Option(None, "--measurement-id"),
    statistical_result_id: str | None = typer.Option(None, "--statistical-result-id"),
    relation_type: str | None = typer.Option(None, "--relation-type"),
    qualification: str | None = typer.Option(None, "--qualification"),
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
            claim_id=option_uuid(claim_id, "--claim-id", runtime.request_id),
            claim_version_id=option_uuid(
                claim_version_id, "--claim-version-id", runtime.request_id
            ),
            measurement_id=option_uuid(measurement_id, "--measurement-id", runtime.request_id),
            statistical_result_id=option_uuid(
                statistical_result_id, "--statistical-result-id", runtime.request_id
            ),
            relation_type=relation_type,
            qualification=qualification,
            expected_row_version=option_int(
                expected_row_version, "--expected-row-version", runtime.request_id
            ),
        )
        return runtime.services.application.link_evidence(
            LinkEvidenceCommand(
                claim_id=uuid_value(values, "claim_id", runtime.request_id),
                claim_version_id=uuid_value(values, "claim_version_id", runtime.request_id),
                measurement_id=optional_uuid_from_values(values, "measurement_id", runtime),
                statistical_result_id=optional_uuid_from_values(
                    values, "statistical_result_id", runtime
                ),
                relation_type=enum_value(
                    values, "relation_type", EvidenceRelationType, runtime.request_id
                ),
                qualification=optional_text(values, "qualification", runtime.request_id),
                expected_row_version=int_value(values, "expected_row_version", runtime.request_id),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def claim_freeze(
    ctx: typer.Context,
    claim_id: str | None = typer.Option(None, "--claim-id"),
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
            claim_id=option_uuid(claim_id, "--claim-id", runtime.request_id),
            version_id=option_uuid(version_id, "--version-id", runtime.request_id),
            expected_row_version=option_int(
                expected_row_version, "--expected-row-version", runtime.request_id
            ),
        )
        return runtime.services.application.freeze_claim_version(
            FreezeClaimVersionCommand(
                claim_id=uuid_value(values, "claim_id", runtime.request_id),
                version_id=uuid_value(values, "version_id", runtime.request_id),
                expected_row_version=optional_positive_int(values, "expected_row_version", runtime),
                context=execution_context(runtime),
            )
        )

    invoke(runtime, json_mode, operation)


def claim_trace(
    ctx: typer.Context,
    claim_version_id: str | None = typer.Option(None, "--claim-version-id"),
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
            claim_version_id=option_uuid(
                claim_version_id, "--claim-version-id", runtime.request_id
            ),
        )
        return runtime.services.provenance.trace_claim_to_runs(
            uuid_value(values, "claim_version_id", runtime.request_id)
        )

    invoke(runtime, json_mode, operation)


def optional_positive_int(values: dict[str, object], name: str, runtime: CliRuntime) -> int | None:
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


def register(app: typer.Typer) -> None:
    claim = command_group("Claim and evidence commands.")
    add_command(claim, "create", "Create a claim.", claim_create)
    add_command(claim, "revise", "Create a new claim version.", claim_revise)
    add_command(claim, "add-evidence", "Attach evidence to a claim version.", claim_add_evidence)
    add_command(claim, "freeze", "Freeze a claim version.", claim_freeze)
    add_command(claim, "trace", "Read exact claim-to-run provenance.", claim_trace)
    app.add_typer(claim, name="claim")
