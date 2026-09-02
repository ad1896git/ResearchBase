from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from typer.testing import CliRunner

from researchbase.cli.app import create_app


@dataclass
class Services:
    application: Any = None
    provenance: Any = None
    governance: Any = None
    governance_queries: Any = None


COMMANDS = {
    "project": ("create",),
    "rq": ("create", "revise", "freeze"),
    "hypothesis": ("create", "revise", "freeze"),
    "spec": ("create", "revise", "freeze"),
    "dataset": ("create", "snapshot"),
    "artifact": ("create", "revise", "freeze"),
    "metric": ("create", "revise", "freeze"),
    "run": ("create", "add-dataset", "add-artifact", "start", "finish", "provenance"),
    "measurement": ("create",),
    "stats": ("create",),
    "claim": ("create", "revise", "add-evidence", "freeze", "trace"),
    "audit": ("create",),
    "impact": ("assess", "show"),
    "correction": ("create",),
}


def test_every_frozen_command_is_registered_and_supports_json() -> None:
    app = create_app(Services())
    runner = CliRunner()
    total = 0
    for group, commands in COMMANDS.items():
        group_help = runner.invoke(app, [group, "--help"])
        assert group_help.exit_code == 0
        for command in commands:
            total += 1
            help_result = runner.invoke(app, [group, command, "--help"])
            assert help_result.exit_code == 0, (group, command, help_result.stderr)
            assert "--json" in help_result.stdout
            assert command in group_help.stdout
    assert total == 35


def test_decision_and_later_phase_commands_are_not_registered() -> None:
    result = CliRunner().invoke(create_app(Services()))
    for forbidden in ("decision", "approval", "orchestrate", "phase2", "phase3"):
        assert forbidden not in result.stdout.lower()
