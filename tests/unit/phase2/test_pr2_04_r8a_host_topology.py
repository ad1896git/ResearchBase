"""Current authorized head and frozen PR2-04 prefix; historical R8A rejection cases."""

import hashlib
import subprocess
from pathlib import Path

import pytest
from scripts.pr2_04_host_acceptance_tests import (
    _validate_current_r8a_migrations,
    validate_r8a_migration_topology,
)


def test_r8a_actual_migration_graph_and_frozen_bytes():
    result = _validate_current_r8a_migrations()
    from scripts.pr2_04_recovery_bindings import historical_gate_scope

    assert result == historical_gate_scope()
    assert result["status"] == "NOT_APPLICABLE"
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    # Later authorized children do not invalidate the frozen PR2-04 migration prefix.
    root = Path(__file__).resolve().parents[3]
    frozen = "eac3153cd3ba96797d63593827ec58fc8d3fc1a6"
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", frozen, "--", "migrations/versions"],
        cwd=root,
        text=True,
    ).splitlines()
    assert "migrations/versions/0028_provider_cancellation.py" in paths
    for name in paths:
        original = subprocess.check_output(["git", "show", f"{frozen}:{name}"], cwd=root)
        assert (
            hashlib.sha256((root / name).read_bytes()).digest() == hashlib.sha256(original).digest()
        )
    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    assert scripts.get_heads() == ["0065_b22_prior_art_correction"]
    assert (
        scripts.get_revision(scripts.get_heads()[0]).down_revision == "0064_b14_publication_ready"
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "extra_file",
        "missing_history",
        "changed_history",
        "old_head",
        "two_heads",
        "wrong_parent",
        "missing_child",
    ],
)
def test_r8a_host_rejects_unauthorized_migration_topology(mutation):
    old = {"migrations/versions/0024_literature_search_execution.py": b"frozen"}
    child = "migrations/versions/0025_pr2_04_reservation_guards.py"
    current = {**old, child: b"authorized child"}
    heads = ["0025_pr2_04_reservation_guards"]
    parent = "0024_literature_search_execution"
    validate_r8a_migration_topology(old, current, heads, parent)
    if mutation == "extra_file":
        current["migrations/versions/0026_unauthorized.py"] = b"extra"
    elif mutation == "missing_history":
        current.pop(next(iter(old)))
    elif mutation == "changed_history":
        current[next(iter(old))] = b"modified"
    elif mutation == "old_head":
        heads = [parent]
    elif mutation == "two_heads":
        heads.append("unauthorized")
    elif mutation == "wrong_parent":
        parent = "0023a_search_plan_review_guards"
    elif mutation == "missing_child":
        current.pop(child)
    with pytest.raises(AssertionError):
        validate_r8a_migration_topology(old, current, heads, parent)
