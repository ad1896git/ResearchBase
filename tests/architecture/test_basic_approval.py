"""Bounded Approval architecture; no effect command or parallel scientific truth."""

import ast
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[2]


def test_approval_domain_and_application_boundaries():
    for layer in ("domain", "application"):
        p = ROOT / f"src/researchbase/{layer}/approval.py"
        tree = ast.parse(p.read_text())
        imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        assert not any(
            m
            and m.startswith(
                ("sqlalchemy", "fastapi", "typer", "researchbase.persistence", "codex")
            )
            for m in imports
        )


def test_no_approval_effect_surface():
    source = (ROOT / "src/researchbase/application/approval.py").read_text()
    tree = ast.parse(source)
    names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert {
        "request_approval",
        "decide_approval",
        "get_request",
        "get_decision",
        "get_grant",
    } <= names
    assert (
        not {
            "record_internal_scientific_release",
            "transition_publication_ready",
            "freeze_prepared_submission",
            "consume_grant",
            "record_revision_action",
        }
        & names
    )
    assert (
        "ON DELETE CASCADE"
        not in (ROOT / "migrations/versions/0045_pr2_16_basic_approval.py").read_text()
    )


def test_single_forward_revision():
    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    assert scripts.get_heads() == ["0073_b02_strategy_admission"]
    assert (
        scripts.get_revision(scripts.get_heads()[0]).down_revision
        == "0072_b03_discussion_hypothesis"
    )
