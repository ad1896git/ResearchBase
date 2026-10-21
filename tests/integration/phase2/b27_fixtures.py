"""Narrow privileged mutations in disposable PostgreSQL databases only."""

from contextlib import contextmanager

from sqlalchemy import text

# Each mutation bypasses only the guards and FK on the selected stored edge.
GUARDS = {
    ("source_versions", "predecessor_source_version_id"): (
        "trg_source_version_guard",
        "trg_source_version_refs_valid",
    ),
    ("source_versions", "literature_source_id"): ("trg_source_version_guard",),
    ("evidence_relations", "statistical_result_id"): (
        "evidence_relations_draft_only",
        "pr17d_evidence_relation_update",
    ),
    ("statistical_result_inputs", "measurement_id"): (
        "statistical_result_inputs_immutable",
        "pr17d_statistical_result_input_update",
    ),
    ("runs", "experiment_spec_version_id"): ("pr17d_run_update",),
    ("experiment_spec_versions", "experiment_spec_id"): ("pr17d_experiment_spec_version_update",),
    ("metric_definition_versions", "metric_definition_id"): (
        "metric_definition_versions_frozen_immutable",
        "pr17d_metric_definition_version_update",
    ),
    ("evidence_relations", "measurement_id"): (
        "evidence_relations_draft_only",
        "pr17d_evidence_relation_update",
    ),
    ("scientific_conclusion_claim_inputs", "claim_version_id"): ("pr211_claim_input_guard",),
    ("scientific_conclusion_claim_inputs", "literature_support_snapshot_id"): (
        "pr211_claim_input_guard",
    ),
    ("scientific_conclusion_literature_inputs", "literature_evidence_id"): (
        "pr211_literature_input_guard",
    ),
    ("literature_evidence", "source_version_id"): ("m3_evidence_guard",),
    ("decision_basis_reviews", "internal_review_record_id"): ("pr215_review_basis_immutable",),
    ("decision_basis_conclusions", "scientific_conclusion_version_id"): (
        "pr215_conclusion_basis_immutable",
    ),
    ("search_coverage", "search_plan_version_id"): ("trg_pr218_search_coverage_immutable",),
    ("prior_art_relations", "claim_version_id"): ("trg_pr218_prior_art_relations_immutable",),
    ("novelty_assessments", "claim_version_id"): ("trg_pr218_novelty_assessments_immutable",),
}


@contextmanager
def exact_edge_bypass(connection, table, column):
    guards = GUARDS[(table, column)]  # fixed allowlist, never caller SQL identifiers
    assert connection.execute(
        text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")
    ).scalar_one()
    constraints = (
        connection.execute(
            text("""SELECT c.conname FROM pg_constraint c
        JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=ANY(c.conkey)
        WHERE c.conrelid=CAST(:table AS regclass) AND c.contype='f' AND a.attname=:column"""),
            {"table": table, "column": column},
        )
        .scalars()
        .all()
    )
    assert constraints
    incoming = {
        (
            "source_versions",
            "literature_source_id",
        ): "fk_literature_sources_current_version_same_source",
        (
            "experiment_spec_versions",
            "experiment_spec_id",
        ): "fk_experiment_specs_current_version_same_parent",
        (
            "metric_definition_versions",
            "metric_definition_id",
        ): "fk_metric_definitions_current_version_same_parent",
    }.get((table, column))
    if incoming:
        assert (
            connection.execute(
                text("SELECT count(*) FROM pg_constraint WHERE conname=:name"), {"name": incoming}
            ).scalar_one()
            == 1
        )
        constraints.append(incoming)
    fk_triggers = (
        connection.execute(
            text("""SELECT tgname FROM pg_trigger t
        JOIN pg_constraint c ON c.oid=t.tgconstraint
        WHERE t.tgrelid=CAST(:table AS regclass) AND c.conname=ANY(:names)"""),
            {"table": table, "names": constraints},
        )
        .scalars()
        .all()
    )
    assert fk_triggers
    names = (*guards, *fk_triggers)
    states = dict(
        connection.execute(
            text("""SELECT tgname,tgenabled FROM pg_trigger
        WHERE tgrelid=CAST(:table AS regclass) AND tgname=ANY(:names)"""),
            {"table": table, "names": list(names)},
        ).all()
    )
    assert set(states) == set(names)
    assert set(states.values()) == {"O"}
    for name in names:
        connection.exec_driver_sql(f'ALTER TABLE "{table}" DISABLE TRIGGER "{name}"')
    try:
        yield
    finally:
        connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        for name in reversed(names):
            connection.exec_driver_sql(f'ALTER TABLE "{table}" ENABLE TRIGGER "{name}"')
        restored = dict(
            connection.execute(
                text("""SELECT tgname,tgenabled FROM pg_trigger
            WHERE tgrelid=CAST(:table AS regclass) AND tgname=ANY(:names)"""),
                {"table": table, "names": list(names)},
            ).all()
        )
        assert restored == states


def corrupt_edge(engine, table, column, identity, missing, *, key="id"):
    assert (table, column) in GUARDS
    assert key in {"id", "decision_id", "conclusion_version_id", "statistical_result_id"}
    with engine.begin() as connection:
        with exact_edge_bypass(connection, table, column):
            result = connection.execute(
                text(f'UPDATE "{table}" SET "{column}"=:missing WHERE "{key}"=:id'),
                {"missing": missing, "id": identity},
            )
            assert result.rowcount > 0
    # A separate connection witnesses committed corruption and restored guards.
    with engine.connect() as connection:
        assert (
            connection.execute(
                text(f'SELECT "{column}" FROM "{table}" WHERE "{key}"=:id'), {"id": identity}
            ).scalar_one()
            == missing
        )


def remove_snapshot_member(engine, snapshot):
    """A single named immutable guard; keep every FK enabled for DELETE."""
    with engine.begin() as conn:
        state = conn.execute(
            text("""SELECT tgenabled FROM pg_trigger
            WHERE tgrelid='literature_evidence_relations'::regclass AND tgname='m3_immutable'""")
        ).scalar_one()
        assert state == "O"
        conn.exec_driver_sql(
            "ALTER TABLE literature_evidence_relations DISABLE TRIGGER m3_immutable"
        )
        try:
            assert (
                conn.execute(
                    text("""DELETE FROM literature_evidence_relations
                WHERE literature_support_snapshot_id=:id"""),
                    {"id": snapshot},
                ).rowcount
                == 1
            )
        finally:
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            conn.exec_driver_sql(
                "ALTER TABLE literature_evidence_relations ENABLE TRIGGER m3_immutable"
            )
            assert (
                conn.execute(
                    text("""SELECT tgenabled FROM pg_trigger
                WHERE tgrelid='literature_evidence_relations'::regclass
                AND tgname='m3_immutable'""")
                ).scalar_one()
                == state
            )
