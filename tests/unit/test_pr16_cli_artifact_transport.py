from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from typer.testing import CliRunner

from researchbase.cli.app import create_app


@dataclass
class ArtifactApplication:
    command: object | None = None

    def create_artifact_version(self, command: object) -> object:
        self.command = command
        return {"ok": True}


@dataclass
class Services:
    application: Any
    provenance: Any = None
    governance: Any = None
    governance_queries: Any = None


def test_artifact_json_payload_decodes_base64_and_preserves_zero_byte_size() -> None:
    application = ArtifactApplication()
    result = CliRunner().invoke(
        create_app(Services(application)),
        [
            "--actor-id",
            str(uuid4()),
            "artifact",
            "revise",
            "--artifact-id",
            str(uuid4()),
            "--json-input",
            '{"data_base64":"aGVsbG8=","byte_size":0}',
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout == '{"ok":true}\n'
    assert application.command is not None
    assert application.command.data == b"hello"  # type: ignore[attr-defined]
    assert application.command.byte_size == 0  # type: ignore[attr-defined]


def test_artifact_json_payload_rejects_invalid_base64_without_application_call() -> None:
    application = ArtifactApplication()
    result = CliRunner().invoke(
        create_app(Services(application)),
        [
            "--actor-id",
            str(uuid4()),
            "artifact",
            "revise",
            "--artifact-id",
            str(uuid4()),
            "--json-input",
            '{"data_base64":"!bad!"}',
            "--json",
        ],
    )

    assert result.exit_code == 2
    assert result.stdout == ""
    assert '"code":"VALIDATION_ERROR"' in result.stderr
    assert application.command is None
