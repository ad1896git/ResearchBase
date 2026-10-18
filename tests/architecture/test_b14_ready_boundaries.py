"""B14 stays within Publication/Application and B13 concrete consumption ownership."""

import inspect
from pathlib import Path

from researchbase.application.approval import ApprovalService
from researchbase.application.publication import PublicationService
from researchbase.persistence.approval_repository import B13_SNAPSHOT_TABLES
from researchbase.persistence.manuscript_freeze_repository import B04_SNAPSHOT_TABLES

ROOT = Path(__file__).resolve().parents[2]


def test_first_inventory_is_frozen_exact_and_excludes_writer():
    expected = tuple(
        sorted(
            set(B04_SNAPSHOT_TABLES)
            | {
                "manuscript_versions",
                "internal_review_records",
                "review_issues",
                "review_issue_events",
            }
        )
    )
    assert B13_SNAPSHOT_TABLES == expected
    assert "publications" not in expected
    assert "consent" not in " ".join(expected)


def test_common_boundary_single_uow_b13_ownership():
    source = inspect.getsource(PublicationService.transition_publication_ready)
    assert "VerifiedPrincipal" not in source  # common principal policy, no caller branching
    assert "_consume_ready_in_uow" in source and "consuming=True" in source
    assert source.index("prepare_write()") < source.index("lock_lifecycle(")
    consumption = inspect.getsource(ApprovalService._consume_ready_in_uow)
    assert "self._factory()" not in consumption and "uow.commit()" not in consumption
    assert "transition_ready" in consumption and "insert_consumption" in consumption
    assert consumption.index("force_constraints()") < consumption.index("final_at =")
    assert "_issuer_live" in consumption


def test_reads_are_snapshot_only_without_exclusion_or_writes():
    for method in (
        PublicationService._read_ready,
        PublicationService._ready_readback,
        ApprovalService._receipt_view,
        ApprovalService._prepare_read,
    ):
        source = inspect.getsource(method)
        for forbidden in (
            "lock_project(",
            "lock_scope(",
            "lock_lifecycle(",
            "prepare_write(",
            ".commit(",
            "FOR UPDATE",
            "FOR SHARE",
            "LOCK TABLE",
            "admission=True",
        ):
            assert forbidden not in source
    assert "readonly=True" in inspect.getsource(ApprovalService._prepare_read)


def test_concrete_graph_no_new_schema_or_transport():
    source = (ROOT / "migrations/versions/0064_b14_publication_ready.py").read_text()
    upgrade = source.split("DOWNGRADE_SQL =")[0]
    for token in (
        "REFERENCES decision_records(id) ON DELETE RESTRICT",
        "REFERENCES approval_grant_consumptions(id) ON DELETE RESTRICT DEFERRABLE",
        "b14_complete_ready_consumption",
        "xmin=pg_current_xact_id()::xid",
    ):
        assert token in upgrade
    for token in ("CREATE TABLE", "ADD COLUMN", "ON DELETE CASCADE", "consumption_reviews"):
        assert token not in upgrade
    for path in ("src/researchbase/api", "src/researchbase/cli"):
        for file in (ROOT / path).glob("*.py"):
            assert "def transition_publication_ready" not in file.read_text()


def test_mirrored_scientific_material_keeps_owning_hash_contracts():
    import re

    def function(path, name):
        source = (ROOT / path).read_text()
        match = re.search(
            r"CREATE (?:OR REPLACE )?FUNCTION " + name + r"\(.*?END \$\$;", source, re.S
        )
        assert match is not None
        return match.group(0)

    def normalized(sql):
        return "\n".join(line.strip() for line in sql.splitlines()).strip()

    origin = "migrations/versions/0045_pr2_16_basic_approval.py"
    new = "migrations/versions/0064_b14_publication_ready.py"
    facts = function(origin, "pr216_facts")
    adapted = facts.replace("pr216_facts(", "b14_facts(", 1).replace(
        "pr216_closure(target)", "b11_closure(target)"
    )
    assert normalized(function(new, "b14_facts")) == normalized(adapted)
    material = function(origin, "pr216_material_gate")
    mirror = normalized(function(new, "b14_material"))
    blocks = (
        ("      SELECT coalesce(jsonb_agg", "      FOR cv IN SELECT"),
        ("        IF cv.status NOT IN", "      END LOOP;"),
        ("      IF EXISTS(WITH effective", "      FOR review_row IN SELECT"),
    )
    for start, end in blocks:
        block = material[material.index(start) : material.index(end, material.index(start))]
        assert normalized(block.replace("r.project_id", "pid")) in mirror
