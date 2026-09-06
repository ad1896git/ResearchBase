from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from researchbase.cli.app import create_app


def test_phase1_examples_use_only_registered_routes_and_commands() -> None:
    document = Path("docs/phase1_api_cli_examples.md").read_text(encoding="utf-8")
    for route in (
        "/v1/projects",
        "/v1/runs/RUN_ID/provenance",
        "/v1/claim-versions/CLAIM_VERSION_ID/trace",
        "/v1/impact/artifact_version/ARTIFACT_VERSION_ID",
    ):
        assert route in document
    for command in (
        "project create",
        "run provenance",
        "claim trace",
        "impact show",
    ):
        assert command in document
    assert "phase2" not in document.lower()
    assert "orchestrate" not in document.lower()


def test_phase1_cli_examples_are_registered() -> None:
    runner = CliRunner()
    app = create_app()
    for command in (
        ["project", "create", "--help"],
        ["run", "provenance", "--help"],
        ["claim", "trace", "--help"],
        ["impact", "show", "--help"],
    ):
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.stderr
