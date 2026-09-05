from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from typer.testing import CliRunner

from researchbase.application.commands import WriteProjectionTarget
from researchbase.application.dto import WriteResult
from researchbase.cli.app import create_app
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


@dataclass
class TransportApplication:
    error: BaseException | None = None
    calls: dict[str, int] | None = None

    def __post_init__(self) -> None:
        self.calls = {}

    def _call(self, name: str) -> WriteResult:
        assert self.calls is not None
        self.calls[name] = self.calls.get(name, 0) + 1
        if self.error is not None:
            raise self.error
        return WriteResult(id=uuid4(), server_timestamp=datetime.now(UTC))

    def project_write_result(self, result: WriteResult, target: WriteProjectionTarget) -> object:
        assert target in {
            WriteProjectionTarget.PROJECT,
            WriteProjectionTarget.RUN,
        }
        return {"ok": True}

    def create_project(self, command: object) -> object:
        return self._call("create_project")

    def start_run(self, command: object) -> object:
        return self._call("start_run")

    def finish_run(self, command: object) -> object:
        return self._call("finish_run")


@dataclass
class Services:
    application: Any
    provenance: Any = None
    governance: Any = None
    governance_queries: Any = None


def invoke(fake: TransportApplication, args: list[str]):
    return CliRunner().invoke(
        create_app(Services(fake)),
        ["--actor-id", str(uuid4()), *args],
    )


def test_transport_attack_matrix_never_calls_application(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    cases = [
        ["--actor-id", "bad", "project", "create", "--name", "P"],
        ["--request-id", "bad", "project", "create", "--name", "P"],
        ["--correlation-id", "bad", "project", "create", "--name", "P"],
        ["--causation-id", "bad", "project", "create", "--name", "P"],
        ["project", "create", "--name", "P", "--json-input", "{"],
        ["project", "create", "--name", "P", "--json-file", str(missing)],
        [
            "run",
            "finish",
            "--run-id",
            str(uuid4()),
            "--outcome",
            "not-a-status",
            "--expected-row-version",
            "1",
        ],
        ["project", "create"],
        ["run", "start", "--run-id", str(uuid4()), "--expected-row-version", "wrong"],
        ["project", "create", "--name", "P", "--unexpected"],
    ]
    for args in cases:
        fake = TransportApplication()
        result = invoke(fake, args)
        assert result.exit_code == 2, (args, result.stdout, result.stderr)
        assert "request_id=" in result.stderr or '"request_id"' in result.stderr
        assert fake.calls == {}


def test_json_transport_error_has_one_stderr_document_and_empty_stdout() -> None:
    fake = TransportApplication()
    result = invoke(fake, ["project", "create", "--json-input", "{", "--json"])

    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr.count("\n") == 1
    assert '"code":"VALIDATION_ERROR"' in result.stderr
    assert fake.calls == {}


def test_cli_invocation_recovers_after_success_error_transport_and_internal_error() -> None:
    fake = TransportApplication()
    runner = CliRunner()
    app = create_app(Services(fake))

    success = ["project", "create", "--name", "P"]
    assert runner.invoke(app, ["--actor-id", str(uuid4()), *success]).exit_code == 0

    fake.error = ResearchBaseError(ErrorCode.NOT_FOUND, "missing")
    assert runner.invoke(app, ["--actor-id", str(uuid4()), *success]).exit_code == 3
    fake.error = None
    assert runner.invoke(app, ["--actor-id", str(uuid4()), *success]).exit_code == 0

    transport = runner.invoke(app, ["--actor-id", str(uuid4()), "project", "create"])
    assert transport.exit_code == 2
    assert runner.invoke(app, ["--actor-id", str(uuid4()), *success]).exit_code == 0

    fake.error = RuntimeError("private persistence detail")
    internal = runner.invoke(app, ["--actor-id", str(uuid4()), *success])
    assert internal.exit_code == 70
    assert "private persistence detail" not in internal.stderr
    fake.error = None
    assert runner.invoke(app, ["--actor-id", str(uuid4()), *success]).exit_code == 0
