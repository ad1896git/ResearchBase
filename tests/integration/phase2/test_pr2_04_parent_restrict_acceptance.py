"""Real deletes of referenced parents preserve frozen execution provenance."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.integration.phase2.test_pr2_04_schema_coverage import A, E, Q, _material, _rows


@pytest.mark.pr204_requirements("PR204-DB-01")
@pytest.mark.parametrize("parent", ["actors", "projects", "literature_search_plan_versions", E, A, Q])
def test_pg_referenced_parent_delete_cannot_remove_provenance(parent, phase2_database_url,
                                                             pr204_trace):
    material = _material(phase2_database_url, "sealed")
    engine = material["engine"]
    try:
        before = _rows(engine)
        target = {
            "actors": material["principal"].actor_id, "projects": material["project"],
            "literature_search_plan_versions": material["version"], E: material["execution"],
            A: before[A][0]["id"], Q: before[Q][0]["id"],
        }[parent]
        with pytest.raises(DBAPIError) as caught:
            with engine.begin() as connection:
                connection.execute(text(f"DELETE FROM {parent} WHERE id=:id"), {"id": target})
        state = getattr(caught.value.orig, "sqlstate", None)
        # An immutable-parent trigger can reject before PostgreSQL checks its RESTRICT FK.
        # Existing catalog inventory separately proves every FK's RESTRICT declaration.
        assert state in {"23503", "P17D1"}
        assert _rows(engine) == before
        pr204_trace.record(parent_table=parent, rejected_sqlstate=state,
                           constraint=getattr(getattr(caught.value.orig, "diag", None), "constraint_name", None),
                           before=before, after=_rows(engine), provider_calls=len(material["provider"].calls))
    finally:
        engine.dispose()
