"""Host topology rejects any extension beyond the authorized R8A child."""

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

    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    assert scripts.get_heads() == ["0027_pr2_04_hash_scheme_guards"]
    assert (
        scripts.get_revision(scripts.get_heads()[0]).down_revision
        == "0026_pr2_04_p1_contract_guards"
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
